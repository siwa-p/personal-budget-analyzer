from datetime import datetime
from typing import List

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, status
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.core.logger_init import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/category-distribution", status_code=status.HTTP_200_OK)
def get_category_distribution(
    *,
    db: Session = Depends(deps.get_db),
    start_date: datetime = datetime.now().replace(day=1, month=1),
    end_date: datetime = datetime.now(),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    stmt = (
        select(
            models.Category.name.label("category_name"),
            func.sum(models.Transactions.amount).label("total_amount")
        )
        .join(models.Category, models.Transactions.category_id == models.Category.id)
        .where(
            models.Transactions.user_id == current_user.id,
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
    db: Session = Depends(deps.get_db),
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    start_date = datetime(start_year, start_month, 1)
    # Get last day of end month
    if end_month == 12:
        end_date = datetime(end_year + 1, 1, 1) - relativedelta(days=1)
    else:
        end_date = datetime(end_year, end_month + 1, 1) - relativedelta(days=1)

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