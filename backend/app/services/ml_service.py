import re

import pendulum
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logger_init import setup_logging
from app.models.category import Category
from app.models.transaction import Transactions

logger = setup_logging()


_model_cache: dict[int, tuple[Pipeline, list[str], pendulum.DateTime]] = {}

MODEL_TTL = pendulum.duration(hours=24)
MIN_TRAINING_SAMPLES = 5
MIN_CLASSES = 2
CONFIDENCE_THRESHOLD = 0.45

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
    ), 'Dining Out'),
    (re.compile(
        r'\b(uber|lyft|taxi|bus|metro|subway|train|gas|gasoline'
        r'|fuel|parking|toll|transit|rideshare)\b',
        re.IGNORECASE,
    ), 'Transport'),
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
    ), 'Healthcare'),
    (re.compile(r'\b(rent|mortgage|lease|landlord|housing)\b', re.IGNORECASE), 'Rent'),
    (re.compile(r'\b(salary|payroll|paycheck|wage|direct\s*deposit)\b', re.IGNORECASE), 'Salary'),
    (re.compile(r'\b(freelance|consulting|invoice|contract|client\s*payment)\b', re.IGNORECASE), 'Freelance'),
]


def _get_training_data(db: Session, user_id: int) -> list[tuple[str, str]]:
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
    return [(desc.strip(), cat_name) for desc, cat_name in rows if desc and desc.strip()]


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
    cached = _model_cache.get(user_id)
    if cached:
        pipeline, classes, trained_at = cached
        if pendulum.now("UTC") - trained_at < MODEL_TTL:
            logger.debug(f"User {user_id}: using cached ML model (trained at {trained_at})")
            return pipeline, classes
        logger.info(f"User {user_id}: cached model expired, retraining")

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
        _model_cache[user_id] = (pipeline, classes, pendulum.now("UTC"))
        logger.info(f"User {user_id}: model trained successfully, classes={classes}")
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
    logger.info(f"User {user_id}: ML model cache invalidated")
    _model_cache.pop(user_id, None)
