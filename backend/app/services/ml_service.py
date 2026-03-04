import hashlib
import hmac
import json
import pickle
import re
from datetime import UTC, datetime

import redis as redis_lib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger_init import setup_logging
from app.models.category import Category
from app.models.transaction import Transactions

logger = setup_logging()

# L1: in-process cache (fast, invalidated on corrections or restart)
_model_cache: dict[int, tuple[Pipeline, list[str]]] = {}

# Best-config L1 cache — survives until process restart; updated after each tune run
_best_config_cache: dict[int, dict] = {}

# L2: Redis (24h TTL, survives restarts, shared across workers)
_redis_client: redis_lib.Redis | None = None
_redis_checked: bool = False
_REDIS_KEY_PREFIX = "ml_model:v1:"
_BEST_CONFIG_KEY_PREFIX = "ml_best_config:v1:"
MODEL_TTL_SECONDS = 24 * 60 * 60        # 24 hours
BEST_CONFIG_TTL_SECONDS = 30 * 24 * 3600  # 30 days

RETUNE_GROWTH_THRESHOLD = 0.25  # retune when data grows >= 25%
RETUNE_AGE_DAYS = 7             # retune if last tune was more than this many days ago

MIN_TRAINING_SAMPLES = 5
MIN_CLASSES = 2
MIN_CLASS_FOR_CV = 4   # classes with fewer samples are excluded from CV / tuning
CONFIDENCE_THRESHOLD = 0.45
CORRECTION_WEIGHT = 3

KEYWORD_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(
        r'\b(grocery|groceries|supermarket|walmart|kroger'
        r'|whole\s*foods|trader\s*joe|aldi|safeway|publix|costco)\b',
        re.IGNORECASE,
    ), 'Groceries'),
    (re.compile(
        r'\b(restaurant|dinner|lunch|breakfast|cafe|coffee|starbucks|mcdonald'
        r'|pizza|sushi|takeout|doordash|uber\s*eats|grubhub|chipotle)\b',
        re.IGNORECASE,
    ), 'Dining'),
    (re.compile(
        r'\b(uber|lyft|taxi|bus|metro|subway|train|gas|gasoline'
        r'|fuel|parking|toll|transit|rideshare)\b',
        re.IGNORECASE,
    ), 'Transportation'),
    (re.compile(
        r'\b(electric|electricity|internet|wifi|phone|water bill'
        r'|utility|utilities|at&t|verizon|comcast|t-mobile)\b',
        re.IGNORECASE,
    ), 'Utilities'),
    (re.compile(
        r'\b(netflix|spotify|hulu|disney|movie|cinema|concert'
        r'|ticket|streaming|video\s*game|game|twitch)\b',
        re.IGNORECASE,
    ), 'Entertainment'),
    (re.compile(
        r'\b(amazon|target|clothing|clothes|shoes|apparel'
        r'|shopping|ebay|mall|fashion|wardrobe|outfit)\b',
        re.IGNORECASE,
    ), 'Shopping'),
    (re.compile(
        r'\b(doctor|medical|pharmacy|cvs|walgreens|hospital'
        r'|clinic|dentist|health|medicine|prescription|therapy)\b',
        re.IGNORECASE,
    ), 'Health & Fitness'),
    (re.compile(r'\b(rent|mortgage|lease|landlord|housing)\b', re.IGNORECASE), 'Housing'),
    (re.compile(r'\b(salary|payroll|paycheck|wage|direct\s*deposit)\b', re.IGNORECASE), 'Salary'),
    (re.compile(r'\b(freelance|consulting|invoice|contract|client\s*payment)\b', re.IGNORECASE), 'Freelance'),
]


def _filter_rare_classes(
    samples: list[tuple[str, str]], min_count: int
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Remove samples whose class has fewer than min_count examples.

    Returns (kept_samples, excluded_class_counts).
    This prevents tiny classes from collapsing n_cv_folds to 2 and causing
    CalibratedClassifierCV inner-fold stratification failures.
    """
    from collections import Counter
    counts = Counter(cat for _, cat in samples)
    kept = [(desc, cat) for desc, cat in samples if counts[cat] >= min_count]
    excluded = {cat: cnt for cat, cnt in counts.items() if cnt < min_count}
    return kept, excluded


def _sign(data: bytes) -> bytes:
    """Prepend an HMAC-SHA256 signature so we can verify before unpickling."""
    key = settings.SECRET_KEY.encode()
    sig = hmac.new(key, data, hashlib.sha256).digest()
    return sig + data


def _verify_and_load(signed_data: bytes) -> tuple[Pipeline, list[str]]:
    """Verify signature then unpickle — raises ValueError on tampered data."""
    key = settings.SECRET_KEY.encode()
    sig, data = signed_data[:32], signed_data[32:]
    expected = hmac.new(key, data, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("ML model Redis payload failed HMAC verification")
    return pickle.loads(data)  # noqa: S301 — data verified above


def _get_redis() -> redis_lib.Redis | None:
    """Lazily connect to Redis once; return None if unavailable."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        client = redis_lib.from_url(settings.REDIS_URL, decode_responses=False)
        client.ping()
        _redis_client = client
        logger.info("ML service: Redis connection established")
    except Exception:
        logger.warning("ML service: Redis unavailable, using in-memory cache only")
    return _redis_client


def _save_best_config(user_id: int, config: dict) -> None:
    """Persist the winning tuned config to L1 memory + Redis."""
    _best_config_cache[user_id] = config
    r = _get_redis()
    if r is not None:
        try:
            r.set(
                f"{_BEST_CONFIG_KEY_PREFIX}{user_id}",
                json.dumps(config).encode(),
                ex=BEST_CONFIG_TTL_SECONDS,
            )
            logger.info(f"User {user_id}: best config saved to Redis — model={config['model_name']}")
        except Exception:
            logger.warning(f"User {user_id}: Redis write failed for best config, stored in L1 only")


def _load_best_config(user_id: int) -> dict | None:
    """Load the saved best config from L1, then Redis. Returns None if never tuned."""
    if user_id in _best_config_cache:
        return _best_config_cache[user_id]
    r = _get_redis()
    if r is not None:
        try:
            data = r.get(f"{_BEST_CONFIG_KEY_PREFIX}{user_id}")
            if data:
                config = json.loads(data.decode())
                _best_config_cache[user_id] = config
                logger.info(f"User {user_id}: best config loaded from Redis — model={config['model_name']}")
                return config
        except Exception:
            logger.warning(f"User {user_id}: Redis read failed for best config")
    return None


def _build_pipeline_from_config(config: dict, inner_cv: int = 3) -> Pipeline:
    """Reconstruct a fresh sklearn Pipeline using the saved best-config params."""
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import ComplementNB

    clf_map = {
        "MultinomialNB": MultinomialNB(),
        "ComplementNB": ComplementNB(),
        "SGD_modified_huber": SGDClassifier(loss="modified_huber", random_state=42),
        "SGD_hinge_SVM": CalibratedClassifierCV(
            SGDClassifier(loss="hinge", random_state=42), cv=inner_cv
        ),
        "LogisticRegression": LogisticRegression(max_iter=2000, random_state=42),
    }
    clf = clf_map.get(
        config.get("model_name", ""),
        SGDClassifier(loss="modified_huber", random_state=42),
    )
    pipeline = Pipeline([("tfidf", TfidfVectorizer(min_df=1)), ("clf", clf)])

    params = dict(config.get("params", {}))
    if "tfidf__ngram_range" in params:
        # JSON round-trip turns tuples into lists; sklearn needs a tuple
        params["tfidf__ngram_range"] = tuple(params["tfidf__ngram_range"])
    if params:
        pipeline.set_params(**params)
    return pipeline


def _get_training_data(db: Session, user_id: int) -> list[tuple[str, str]]:
    from app.models.category_feedback import CategoryFeedback  # local import avoids circular dependency

    stmt = (
        select(Transactions.description, Category.name)
        .join(Category, Transactions.category_id == Category.id)
        .where(
            Transactions.user_id == user_id,
            Transactions.description.is_not(None),
            Transactions.description != "",
        )
        .limit(2000)
    )
    rows = db.execute(stmt).all()
    samples = [(desc.strip(), cat_name) for desc, cat_name in rows if desc and desc.strip()]

    feedback_stmt = (
        select(CategoryFeedback.description, Category.name)
        .join(Category, CategoryFeedback.chosen_category_id == Category.id)
        .where(
            CategoryFeedback.user_id == user_id,
            CategoryFeedback.is_correction.is_(True),
            CategoryFeedback.description.is_not(None),
            CategoryFeedback.description != "",
        )
        .limit(500)
    )
    feedback_rows = db.execute(feedback_stmt).all()
    for desc, cat_name in feedback_rows:
        if desc and desc.strip():
            samples.extend([(desc.strip(), cat_name)] * CORRECTION_WEIGHT)

    from collections import Counter
    cat_counts = Counter(cat for _, cat in samples)
    logger.info(
        f"User {user_id}: training data — {len(rows)} transactions + {len(feedback_rows)} corrections "
        f"(x{CORRECTION_WEIGHT}) = {len(samples)} total samples | distribution: {dict(cat_counts)}"
    )
    for desc, cat_name in feedback_rows:
        if desc and desc.strip():
            logger.info(f"  [correction sample x{CORRECTION_WEIGHT}] '{desc}' → '{cat_name}'")

    return samples


def _train_pipeline(
    samples: list[tuple[str, str]], config: dict | None = None
) -> tuple[Pipeline, list[str]]:
    texts = [s[0] for s in samples]
    labels = [s[1] for s in samples]
    if config is not None:
        pipeline = _build_pipeline_from_config(config)
        source = f"tuned ({config['model_name']})"
    else:
        # Default fallback: modified_huber SGD with sensible priors.
        # modified_huber is an SVM-like large-margin loss that natively supports
        # predict_proba (loss="hinge" is a true LinearSVM but lacks predict_proba).
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ("clf", SGDClassifier(loss="modified_huber", penalty="l2", alpha=1e-3, random_state=42, max_iter=100)),
        ])
        source = "default (SGD_modified_huber)"
    logger.info(f"Training pipeline using {source}")
    pipeline.fit(texts, labels)
    return pipeline, list(pipeline.classes_)


def _rule_predict(description: str, available_names: set[str]) -> str | None:
    desc_lower = description.lower()
    for pattern, cat_name in KEYWORD_RULES:
        if pattern.search(desc_lower) and cat_name in available_names:
            return cat_name
    return None


def _get_or_train(db: Session, user_id: int) -> tuple[Pipeline, list[str]] | None:
    # L1: in-process cache
    if user_id in _model_cache:
        logger.debug(f"User {user_id}: ML model served from in-memory cache (L1)")
        return _model_cache[user_id]

    # L2: Redis
    r = _get_redis()
    if r is not None:
        try:
            data = r.get(f"{_REDIS_KEY_PREFIX}{user_id}")
            if data:
                pipeline, classes = _verify_and_load(data)
                _model_cache[user_id] = (pipeline, classes)
                logger.info(f"User {user_id}: ML model loaded from Redis (L2), warm in L1")
                return pipeline, classes
        except Exception:
            logger.warning(f"User {user_id}: Redis read failed, will retrain from DB")

    # Train from DB
    samples = _get_training_data(db, user_id)
    if len(samples) < MIN_TRAINING_SAMPLES:
        logger.info(f"User {user_id}: only {len(samples)} labeled transactions, "
                    f"need {MIN_TRAINING_SAMPLES} — skipping ML")
        return None

    distinct = {label for _, label in samples}
    if len(distinct) < MIN_CLASSES:
        logger.info(f"User {user_id}: only {len(distinct)} distinct categories, need {MIN_CLASSES} — skipping ML")
        return None

    try:
        best_config = _load_best_config(user_id)
        model_label = best_config["model_name"] if best_config else "default SGD_modified_huber"
        logger.info(
            f"User {user_id}: training ML model on {len(samples)} samples across "
            f"{len(distinct)} categories using {model_label}"
        )
        pipeline, classes = _train_pipeline(samples, config=best_config)
        _model_cache[user_id] = (pipeline, classes)
        logger.info(f"User {user_id}: model trained, classes={classes}")

        if r is not None:
            try:
                r.set(
                    f"{_REDIS_KEY_PREFIX}{user_id}",
                    _sign(pickle.dumps((pipeline, classes))),
                    ex=MODEL_TTL_SECONDS,
                )
                logger.info(f"User {user_id}: ML model persisted to Redis (TTL={MODEL_TTL_SECONDS}s)")
            except Exception:
                logger.warning(f"User {user_id}: Redis write failed, model in L1 only")

        return pipeline, classes
    except Exception:
        logger.exception(f"User {user_id}: model training failed")
        return None


def predict_category(
    db: Session,
    user_id: int,
    description: str,
    available_categories: list[dict],
) -> dict:
    _no_suggestion = {"category_id": None, "category_name": None, "confidence": 0.0, "source": "none"}

    if not description or not description.strip():
        return _no_suggestion

    name_to_cat = {c["name"]: c for c in available_categories}
    available_names = set(name_to_cat)

    model_result = _get_or_train(db, user_id)
    if model_result is not None:
        pipeline, classes = model_result
        try:
            proba = pipeline.predict_proba([description])[0]
            best_idx = int(proba.argmax())
            best_name = classes[best_idx]
            confidence = float(proba[best_idx])

            if confidence >= CONFIDENCE_THRESHOLD and best_name in name_to_cat:
                logger.debug(f"User {user_id}: ML predicted '{best_name}' ({confidence:.0%}) for '{description}'")
                cat = name_to_cat[best_name]
                return {
                    "category_id": cat["id"],
                    "category_name": best_name,
                    "confidence": round(confidence, 4),
                    "source": "ml",
                }
            logger.debug(f"User {user_id}: ML confidence too low ({confidence:.0%}) "
                         f"for '{description}', falling back to rules")
        except Exception:
            logger.warning(f"User {user_id}: ML prediction failed for '{description}', falling back to rules")

    matched_name = _rule_predict(description, available_names)
    if matched_name:
        logger.debug(f"User {user_id}: keyword rule matched '{matched_name}' for '{description}'")
        cat = name_to_cat[matched_name]
        return {
            "category_id": cat["id"],
            "category_name": matched_name,
            "confidence": 0.7,
            "source": "rules",
        }

    logger.debug(f"User {user_id}: no suggestion for '{description}'")
    return _no_suggestion


def benchmark_classifiers(db: Session, user_id: int) -> dict:
    import time
    from collections import Counter

    import numpy as np
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_validate
    from sklearn.naive_bayes import ComplementNB
    from sklearn.pipeline import Pipeline as SKPipeline

    raw_samples = _get_training_data(db, user_id)
    if len(raw_samples) < MIN_TRAINING_SAMPLES:
        return {
            "error": f"Not enough training data ({len(raw_samples)} samples, need {MIN_TRAINING_SAMPLES})",
            "n_samples": len(raw_samples),
        }

    # Drop classes with too few samples — they collapse n_cv_folds and break
    # CalibratedClassifierCV's inner stratification.
    samples, excluded_classes = _filter_rare_classes(raw_samples, MIN_CLASS_FOR_CV)
    if excluded_classes:
        logger.info(
            f"User {user_id}: benchmark — excluded rare classes "
            f"(< {MIN_CLASS_FOR_CV} samples): {excluded_classes}"
        )

    distinct = {label for _, label in samples}
    if len(distinct) < MIN_CLASSES:
        return {
            "error": f"Not enough distinct categories after filtering ({len(distinct)}, need {MIN_CLASSES})",
            "n_samples": len(samples),
        }

    texts = [s[0] for s in samples]
    labels = [s[1] for s in samples]
    class_counts = Counter(labels)

    # n_splits: at most 5 folds, but can't exceed the smallest class count
    min_class_count = min(class_counts.values())
    n_splits = max(2, min(5, min_class_count))

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    def _pipe(clf) -> SKPipeline:
        return SKPipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ("clf", clf),
        ])

    # CalibratedClassifierCV wraps hinge-SVM to add predict_proba via Platt scaling.
    # After filtering rare classes, min_class_count >= MIN_CLASS_FOR_CV so we can
    # safely use cv=3 for the inner calibration folds.
    hinge_base = SGDClassifier(loss="hinge", penalty="l2", alpha=1e-3, random_state=42, max_iter=100)
    inner_cv = min(3, n_splits)
    candidates: dict[str, SKPipeline] = {
        "MultinomialNB": _pipe(MultinomialNB(alpha=0.5)),
        "ComplementNB": _pipe(ComplementNB(alpha=0.5)),
        "SGD_modified_huber": _pipe(
            SGDClassifier(loss="modified_huber", penalty="l2", alpha=1e-3, random_state=42, max_iter=100)
        ),
        "SGD_hinge_SVM": _pipe(
            CalibratedClassifierCV(hinge_base, cv=inner_cv)
        ),
        "LogisticRegression": _pipe(
            LogisticRegression(max_iter=1000, C=1.0, random_state=42, solver="lbfgs")
        ),
    }

    scoring = {"accuracy": "accuracy", "f1_macro": "f1_macro", "f1_weighted": "f1_weighted"}

    results: dict[str, dict] = {}
    for name, pipeline in candidates.items():
        try:
            t0 = time.perf_counter()
            cv_res = cross_validate(pipeline, texts, labels, cv=cv, scoring=scoring)
            elapsed = time.perf_counter() - t0
            results[name] = {
                "accuracy":       round(float(np.mean(cv_res["test_accuracy"])), 4),
                "accuracy_std":   round(float(np.std(cv_res["test_accuracy"])), 4),
                "f1_macro":       round(float(np.mean(cv_res["test_f1_macro"])), 4),
                "f1_macro_std":   round(float(np.std(cv_res["test_f1_macro"])), 4),
                "f1_weighted":    round(float(np.mean(cv_res["test_f1_weighted"])), 4),
                "f1_weighted_std": round(float(np.std(cv_res["test_f1_weighted"])), 4),
                "fit_time_s":     round(float(np.mean(cv_res["fit_time"])), 4),
                "score_time_s":   round(float(np.mean(cv_res["score_time"])), 4),
                "total_wall_s":   round(elapsed, 3),
            }
            logger.info(f"User {user_id}: benchmark [{name}] acc={results[name]['accuracy']:.3f} "
                        f"f1_macro={results[name]['f1_macro']:.3f}")
        except Exception:
            logger.exception(f"User {user_id}: benchmark failed for {name}")
            results[name] = {"error": "classifier failed during cross-validation"}

    # rank by f1_macro descending (skip entries with errors)
    ranked = sorted(
        [k for k in results if "f1_macro" in results[k]],
        key=lambda k: results[k]["f1_macro"],
        reverse=True,
    )

    return {
        "n_samples": len(samples),
        "n_classes": len(distinct),
        "classes": sorted(distinct),
        "class_distribution": dict(class_counts),
        "excluded_classes": excluded_classes,
        "n_cv_folds": n_splits,
        "ranking_by_f1_macro": ranked,
        "classifiers": results,
    }


def tune_classifiers(db: Session, user_id: int) -> dict:
    """Grid-search hyperparameters for each classifier and return the best params per model.

    Classes with fewer than MIN_CLASS_FOR_CV samples are excluded so that
    stratified CV folds stay balanced and CalibratedClassifierCV doesn't fail.
    """
    import time
    from collections import Counter

    import numpy as np
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GridSearchCV, StratifiedKFold
    from sklearn.naive_bayes import ComplementNB
    from sklearn.pipeline import Pipeline as SKPipeline

    raw_samples = _get_training_data(db, user_id)
    if len(raw_samples) < MIN_TRAINING_SAMPLES:
        return {
            "error": f"Not enough training data ({len(raw_samples)} samples, need {MIN_TRAINING_SAMPLES})",
            "n_samples": len(raw_samples),
        }

    samples, excluded_classes = _filter_rare_classes(raw_samples, MIN_CLASS_FOR_CV)
    if excluded_classes:
        logger.info(
            f"User {user_id}: tune — excluded rare classes "
            f"(< {MIN_CLASS_FOR_CV} samples): {excluded_classes}"
        )

    distinct = {label for _, label in samples}
    if len(distinct) < MIN_CLASSES:
        return {
            "error": f"Not enough distinct categories after filtering ({len(distinct)}, need {MIN_CLASSES})",
            "n_samples": len(samples),
        }

    texts = [s[0] for s in samples]
    labels = [s[1] for s in samples]
    class_counts = Counter(labels)
    min_class_count = min(class_counts.values())
    n_splits = max(2, min(5, min_class_count))
    inner_cv = min(3, n_splits)

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    def _base_pipe(clf) -> SKPipeline:
        return SKPipeline([
            ("tfidf", TfidfVectorizer(min_df=1)),
            ("clf", clf),
        ])

    hinge_base = SGDClassifier(loss="hinge", random_state=42)

    # (model_name, pipeline, param_grid)
    # Grids are sized to be thorough but not prohibitively slow:
    #   NB models     ~24-48 candidates x n_splits folds
    #   SGD models    ~48 candidates x n_splits folds
    #   LR            ~20 candidates x n_splits folds (3 sub-grids avoid invalid combos)
    candidates: list[tuple[str, SKPipeline, list[dict] | dict]] = [
        (
            "MultinomialNB",
            _base_pipe(MultinomialNB()),
            {
                "tfidf__ngram_range": [(1, 1), (1, 2)],
                "tfidf__sublinear_tf": [True, False],
                "clf__alpha": [0.01, 0.1, 0.5, 1.0, 2.0, 5.0],
            },
        ),
        (
            "ComplementNB",
            _base_pipe(ComplementNB()),
            {
                "tfidf__ngram_range": [(1, 1), (1, 2)],
                "tfidf__sublinear_tf": [True, False],
                "clf__alpha": [0.01, 0.1, 0.5, 1.0, 2.0, 5.0],
                "clf__norm": [True, False],
            },
        ),
        (
            "SGD_modified_huber",
            _base_pipe(SGDClassifier(loss="modified_huber", random_state=42)),
            {
                "tfidf__ngram_range": [(1, 1), (1, 2)],
                "clf__alpha": [1e-4, 1e-3, 1e-2, 0.1],
                "clf__penalty": ["l2", "l1", "elasticnet"],
                "clf__max_iter": [100, 300],
            },
        ),
        (
            "SGD_hinge_SVM",
            _base_pipe(CalibratedClassifierCV(hinge_base, cv=inner_cv)),
            {
                "tfidf__ngram_range": [(1, 1), (1, 2)],
                "clf__estimator__alpha": [1e-4, 1e-3, 1e-2, 0.1],
                "clf__estimator__penalty": ["l2", "l1"],
                "clf__estimator__max_iter": [100, 300],
            },
        ),
        (
            "LogisticRegression",
            _base_pipe(LogisticRegression(max_iter=2000, random_state=42)),
            # Three sub-grids avoid invalid solver/penalty combos
            [
                {   # lbfgs supports l2 and None
                    "tfidf__ngram_range": [(1, 1), (1, 2)],
                    "clf__solver": ["lbfgs"],
                    "clf__penalty": ["l2", None],
                    "clf__C": [0.1, 0.5, 1.0, 5.0, 10.0],
                },
                {   # saga supports l1, l2, and None
                    "tfidf__ngram_range": [(1, 1), (1, 2)],
                    "clf__solver": ["saga"],
                    "clf__penalty": ["l1", "l2"],
                    "clf__C": [0.1, 0.5, 1.0, 5.0, 10.0],
                },
                {
                    "tfidf__ngram_range": [(1, 1), (1, 2)],
                    "clf__solver": ["saga"],
                    "clf__penalty": [None],
                    "clf__C": [1.0],  # ignored when penalty=None
                },
            ],
        ),
    ]

    results: dict[str, dict] = {}
    for name, pipeline, param_grid in candidates:
        try:
            t0 = time.perf_counter()
            gs = GridSearchCV(
                pipeline,
                param_grid,
                cv=cv,
                scoring="f1_macro",
                n_jobs=-1,
                refit=False,
            )
            gs.fit(texts, labels)
            elapsed = time.perf_counter() - t0

            best_idx = int(np.argmax(gs.cv_results_["mean_test_score"]))
            results[name] = {
                "best_f1_macro": round(float(gs.best_score_), 4),
                "best_f1_macro_std": round(float(gs.cv_results_["std_test_score"][best_idx]), 4),
                "best_params": gs.best_params_,
                "n_candidates": len(gs.cv_results_["params"]),
                "search_wall_s": round(elapsed, 2),
            }
            logger.info(
                f"User {user_id}: tune [{name}] best_f1_macro={gs.best_score_:.4f} "
                f"params={gs.best_params_}"
            )
        except Exception:
            logger.exception(f"User {user_id}: tune failed for {name}")
            results[name] = {"error": "tuning failed during grid search"}

    ranked = sorted(
        [k for k in results if "best_f1_macro" in results[k]],
        key=lambda k: results[k]["best_f1_macro"],
        reverse=True,
    )

    # Persist the winner so future predictions use the tuned model
    best_config: dict | None = None
    if ranked:
        winner = ranked[0]
        best_config = {
            "model_name": winner,
            "params": results[winner]["best_params"],
            "f1_macro": results[winner]["best_f1_macro"],
            "f1_macro_std": results[winner]["best_f1_macro_std"],
            "n_samples_at_tune": len(samples),
            "tuned_at": datetime.now(UTC).isoformat(),
            "excluded_classes": excluded_classes,
        }
        _save_best_config(user_id, best_config)
        # Invalidate the trained-model cache so the next prediction retrains
        # using the new tuned hyperparameters.
        invalidate_cache(user_id)
        logger.info(
            f"User {user_id}: best model set to '{winner}' "
            f"(f1_macro={results[winner]['best_f1_macro']:.4f})"
        )

    return {
        "n_samples": len(samples),
        "n_classes": len(distinct),
        "classes": sorted(distinct),
        "class_distribution": dict(class_counts),
        "excluded_classes": excluded_classes,
        "n_cv_folds": n_splits,
        "ranking_by_best_f1_macro": ranked,
        "results": results,
        "saved_config": best_config,
    }


def should_retune(db: Session, user_id: int) -> bool:
    """Return True if a new tune run is recommended.

    Triggers when:
    - No config has been saved yet (first-time setup).
    - Transaction count grew >= RETUNE_GROWTH_THRESHOLD since last tune.
    - Last tune was more than RETUNE_AGE_DAYS days ago.
    """
    config = _load_best_config(user_id)
    if config is None:
        return True

    try:
        tuned_at = datetime.fromisoformat(config["tuned_at"])
        age_days = (datetime.now(UTC) - tuned_at).days
        if age_days >= RETUNE_AGE_DAYS:
            return True
    except Exception:
        return True

    try:
        current_count: int = db.execute(
            select(func.count()).select_from(Transactions).where(
                Transactions.user_id == user_id,
                Transactions.description.is_not(None),
                Transactions.description != "",
            )
        ).scalar_one()
        n_at_tune = config.get("n_samples_at_tune", 0)
        if n_at_tune > 0 and current_count >= n_at_tune * (1 + RETUNE_GROWTH_THRESHOLD):
            return True
    except Exception:
        logger.warning(f"User {user_id}: could not query transaction count for retune check")

    return False


def get_ml_status(db: Session, user_id: int) -> dict:
    """Return the current best-model info for display in the frontend."""
    config = _load_best_config(user_id)
    retune_needed = should_retune(db, user_id)

    if config is None:
        return {
            "has_config": False,
            "needs_retune": retune_needed,
            "model_name": None,
            "params": None,
            "f1_macro": None,
            "f1_macro_std": None,
            "n_samples_at_tune": None,
            "tuned_at": None,
            "excluded_classes": None,
        }

    return {
        "has_config": True,
        "needs_retune": retune_needed,
        "model_name": config["model_name"],
        "params": config["params"],
        "f1_macro": config["f1_macro"],
        "f1_macro_std": config.get("f1_macro_std"),
        "n_samples_at_tune": config["n_samples_at_tune"],
        "tuned_at": config["tuned_at"],
        "excluded_classes": config.get("excluded_classes", {}),
    }


def invalidate_cache(user_id: int) -> None:
    _model_cache.pop(user_id, None)
    r = _get_redis()
    if r is not None:
        try:
            r.delete(f"{_REDIS_KEY_PREFIX}{user_id}")
        except Exception:
            logger.warning(f"User {user_id}: Redis delete failed during cache invalidation")
    logger.info(f"User {user_id}: ML model cache invalidated (L1 + Redis)")
