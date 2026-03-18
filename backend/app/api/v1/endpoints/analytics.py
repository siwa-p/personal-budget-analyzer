from datetime import datetime

import pendulum
from fastapi import APIRouter, status
from sqlalchemy import extract, func, select

from app import models
from app.api.deps import CurrentUser, DbSession
from app.core.logger_init import setup_logging
from app.services.ml_service import compare_classifiers

logger = setup_logging()
router = APIRouter()


@router.get("/ml-compare", status_code=status.HTTP_200_OK)
def get_ml_compare(*, db: DbSession, current_user: CurrentUser):
    """Compare Logistic Regression vs LinearSVM with RandomizedSearchCV tuning and K-fold CV.

    Logs per-fold train_loss and test_loss to MLflow. Expect 20-60s depending on data size.
    """
    result = compare_classifiers(db, current_user.id)
    if "error" in result:
        logger.warning(f"User {current_user.id}: ml-compare skipped — {result['error']}")
    else:
        for clf_name, metrics in result.get("results", {}).items():
            logger.info(
                f"User {current_user.id}: [{clf_name}] "
                f"train_loss={metrics['train_loss']:.4f}  "
                f"test_loss={metrics['test_loss']:.4f}  "
                f"f1_macro={metrics['test_f1_macro']:.4f}  "
                f"tune_f1={metrics['tune_f1_macro']:.4f}"
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
