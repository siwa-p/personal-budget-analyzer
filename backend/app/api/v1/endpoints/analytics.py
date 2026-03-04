from datetime import datetime

import pendulum
from fastapi import APIRouter, status
from sqlalchemy import extract, func, select

from app import models
from app.api.deps import CurrentUser, DbSession
from app.core.logger_init import setup_logging
from app.services.ml_service import benchmark_classifiers, get_ml_status, tune_classifiers

logger = setup_logging()
router = APIRouter()


@router.get("/ml-benchmark", status_code=status.HTTP_200_OK)
def get_ml_benchmark(*, db: DbSession, current_user: CurrentUser):
    result = benchmark_classifiers(db, current_user.id)
    if "error" in result:
        logger.warning(f"User {current_user.id}: ml-benchmark skipped — {result['error']}")
    else:
        for clf_name, metrics in result.get("classifiers", {}).items():
            if "error" in metrics:
                logger.warning(f"User {current_user.id}: [{clf_name}] failed — {metrics['error']}")
            else:
                logger.info(
                    f"User {current_user.id}: [{clf_name}] "
                    f"acc={metrics['accuracy']:.4f}±{metrics['accuracy_std']:.4f}  "
                    f"f1_macro={metrics['f1_macro']:.4f}±{metrics['f1_macro_std']:.4f}  "
                    f"f1_weighted={metrics['f1_weighted']:.4f}  "
                    f"fit={metrics['fit_time_s']:.4f}s  score={metrics['score_time_s']:.4f}s"
                )
        logger.info(
            f"User {current_user.id}: benchmark ranking (f1_macro) — {result['ranking_by_f1_macro']}"
        )
    return result


@router.get("/ml-status", status_code=status.HTTP_200_OK)
def get_ml_status_endpoint(*, db: DbSession, current_user: CurrentUser):
    """Return the active model name, tuned hyperparameters, CV score, and whether a retune is recommended."""
    return get_ml_status(db, current_user.id)


@router.get("/ml-tune", status_code=status.HTTP_200_OK)
def get_ml_tune(*, db: DbSession, current_user: CurrentUser):
    """Grid-search best hyperparameters for each classifier using the user's transaction data.

    Classes with fewer than MIN_CLASS_FOR_CV samples are excluded from the search
    to ensure stable stratified CV folds. Expect this to take 10-60s depending on
    data size.
    """
    result = tune_classifiers(db, current_user.id)
    if "error" in result:
        logger.warning(f"User {current_user.id}: ml-tune skipped — {result['error']}")
    else:
        for clf_name, metrics in result.get("results", {}).items():
            if "error" in metrics:
                logger.warning(f"User {current_user.id}: tune [{clf_name}] failed — {metrics['error']}")
            else:
                logger.info(
                    f"User {current_user.id}: tune [{clf_name}] "
                    f"best_f1_macro={metrics['best_f1_macro']:.4f}  "
                    f"candidates={metrics['n_candidates']}  "
                    f"wall={metrics['search_wall_s']}s  "
                    f"best_params={metrics['best_params']}"
                )
        logger.info(
            f"User {current_user.id}: tune ranking (f1_macro) — {result['ranking_by_best_f1_macro']}"
        )
    return result


@router.get("/category-distribution", status_code=status.HTTP_200_OK)
def get_category_distribution(
    *,
    db: DbSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: CurrentUser
):
    if start_date is None:
        start_date = pendulum.now().start_of("year")
    if end_date is None:
        end_date = pendulum.now()

    stmt = (
        select(
            models.Category.name.label("category_name"),
            func.sum(models.Transactions.amount).label("total_amount")
        )
        .join(models.Category, models.Transactions.category_id == models.Category.id)
        .where(
            models.Transactions.user_id == current_user.id,
            models.Category.type == "expense",
            models.Transactions.transaction_date >= start_date,
            models.Transactions.transaction_date <= end_date
        )
        .group_by(models.Category.name)
        .order_by(func.sum(models.Transactions.amount).desc())
    )
    category_data = db.execute(stmt).all()

    result = {
        "start_date": start_date,
        "end_date": end_date,
        "category_distribution": [
            {
                "category": category_name,
                "total": float(total) if total else 0.0
            }
            for category_name, total in category_data
        ]
    }
    return result

@router.get("/monthly-spending-trend", status_code=status.HTTP_200_OK)
def get_monthly_spending_trend(
    *,
    db: DbSession,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    current_user: CurrentUser
):
    start_date = pendulum.datetime(start_year, start_month, 1)
    end_date = pendulum.datetime(end_year, end_month, 1).end_of("month")

    stmt = (
        select(
            extract("year", models.Transactions.transaction_date).label("year"),
            extract("month", models.Transactions.transaction_date).label("month"),
            func.sum(models.Transactions.amount).label("total_amount")
        )
        .join(models.Category, models.Transactions.category_id == models.Category.id)
        .where(
            models.Transactions.user_id == current_user.id,
            models.Category.type == "expense",
            models.Transactions.transaction_date >= start_date,
            models.Transactions.transaction_date <= end_date
        )
        .group_by(
            extract("year", models.Transactions.transaction_date),
            extract("month", models.Transactions.transaction_date)
        )
        .order_by(
            extract("year", models.Transactions.transaction_date),
            extract("month", models.Transactions.transaction_date)
        )
    )
    trend_data = db.execute(stmt).all()
    result = {
        "start_date": start_date,
        "end_date": end_date,
        "monthly_spending_trend": [
            {
                "year": int(year),
                "month": int(month),
                "total": float(total) if total else 0.0
            }
            for year, month, total in trend_data
        ]
    }
    return result
