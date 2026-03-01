import hashlib
import hmac
import pickle
import re

import redis as redis_lib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger_init import setup_logging
from app.models.category import Category
from app.models.transaction import Transactions

logger = setup_logging()

# L1: in-process cache (fast, invalidated on corrections or restart)
_model_cache: dict[int, tuple[Pipeline, list[str]]] = {}

# L2: Redis (24h TTL, survives restarts, shared across workers)
_redis_client: redis_lib.Redis | None = None
_redis_checked: bool = False
_REDIS_KEY_PREFIX = "ml_model:v1:"
MODEL_TTL_SECONDS = 24 * 60 * 60  # 24 hours

MIN_TRAINING_SAMPLES = 5
MIN_CLASSES = 2
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

    logger.info(
        f"User {user_id}: training data — {len(rows)} transactions + {len(feedback_rows)} corrections "
        f"(x{CORRECTION_WEIGHT}) = {len(samples)} total samples"
    )
    if feedback_rows:
        for desc, cat_name in feedback_rows:
            logger.info(f"  [correction] '{desc}' → '{cat_name}'")

    return samples


def _train_pipeline(samples: list[tuple[str, str]]) -> tuple[Pipeline, list[str]]:
    texts = [s[0] for s in samples]
    labels = [s[1] for s in samples]
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("clf", MultinomialNB(alpha=0.5)),
    ])
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
        logger.info(f"User {user_id}: training ML model on {len(samples)} samples across {len(distinct)} categories")
        pipeline, classes = _train_pipeline(samples)
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


def invalidate_cache(user_id: int) -> None:
    _model_cache.pop(user_id, None)
    r = _get_redis()
    if r is not None:
        try:
            r.delete(f"{_REDIS_KEY_PREFIX}{user_id}")
        except Exception:
            logger.warning(f"User {user_id}: Redis delete failed during cache invalidation")
    logger.info(f"User {user_id}: ML model cache invalidated (L1 + Redis)")
