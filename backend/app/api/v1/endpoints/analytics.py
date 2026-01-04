from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import extract, func, select
from datetime import datetime

from app import models, schemas
from app.api import deps

router = APIRouter()


@router.get("/monthly-spending", status_code=status.HTTP_200_OK)
def get_monthly_spending(
    *,
    db: Session = Depends(deps.get_db),
    year: int = datetime.now().year,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    stmt = (
        select(
            extract("month", models.Transactions.transaction_date).label("month"),
            func.sum(models.Transactions.amount).label("total_amount")
        )
        .join(models.Category, models.Transactions.category_id == models.Category.id)
        .where(
            models.Transactions.user_id == current_user.id,
            models.Category.type == "expense",
            extract("year", models.Transactions.transaction_date) == year
        )
        .group_by(extract("month", models.Transactions.transaction_date))
        .order_by(extract("month", models.Transactions.transaction_date))
    )

    monthly_data = db.execute(stmt).all()

    result = {
        "year": year,
        "monthly_spending": [
            {
                "month": int(month),
                "total": float(total) if total else 0.0
            }
            for month, total in monthly_data
        ],
        "total_annual_spending": sum(total for _, total in monthly_data if total)
    }

    return result

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