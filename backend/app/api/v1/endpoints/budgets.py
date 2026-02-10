from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.logger_init import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/", response_model=schemas.BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    *,
    db: Session = Depends(deps.get_db),
    budget_in: schemas.BudgetCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    logger.info(f"User {current_user.id} is creating budget for {budget_in.year}/{budget_in.month}")

    # If category_id provided, verify it exists and belongs to user or is system category
    if budget_in.category_id:
        deps.validate_category_access(db, budget_in.category_id, current_user.id)

    budget = crud.budget.create(db, obj_in=budget_in, user_id=current_user.id)
    logger.info(f"User {current_user.id} successfully created budget {budget.id}")
    return budget


@router.get("/month", response_model=List[schemas.BudgetWithCategory])
def get_monthly_budgets(
    *,
    db: Session = Depends(deps.get_db),
    year: int,
    month: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    logger.info(f"User {current_user.id} is retrieving budgets for {year}/{month}")

    budgets = crud.budget.get_budgets_for_month(
        db, user_id=current_user.id, year=year, month=month
    )

    result = []
    for budget in budgets:
        spent = crud.budget.get_spending_for_budget(
            db,
            user_id=current_user.id,
            year=year,
            month=month,
            category_id=budget.category_id
        )
        spent_decimal = Decimal(str(spent))

        remaining = budget.amount - spent_decimal
        percentage_used = (spent_decimal / budget.amount * 100) if budget.amount > 0 else 0

        category_name = None
        if budget.category_id:
            category = crud.category.get(db, id=budget.category_id)
            category_name = category.name if category else None

        budget_dict = {
            "id": budget.id,
            "user_id": budget.user_id,
            "year": budget.year,
            "month": budget.month,
            "category_id": budget.category_id,
            "amount": budget.amount,
            "created_at": budget.created_at,
            "updated_at": budget.updated_at,
            "spent": spent,
            "remaining": remaining,
            "percentage_used": percentage_used,
            "category_name": category_name
        }

        result.append(budget_dict)

    return result


@router.get("/{budget_id}", response_model=schemas.BudgetResponse)
def get_budget(
    *,
    budget: models.Budget = Depends(deps.get_user_budget),
):
    """Get a specific budget by ID"""
    return budget


@router.put("/{budget_id}", response_model=schemas.BudgetResponse)
def update_budget(
    *,
    db: Session = Depends(deps.get_db),
    budget: models.Budget = Depends(deps.get_user_budget),
    budget_in: schemas.BudgetUpdate,
):
    """Update a budget amount"""
    logger.info(f"User {budget.user_id} is updating budget {budget.id}")
    budget = crud.budget.update(db, db_obj=budget, obj_in=budget_in)
    logger.info(f"User {budget.user_id} successfully updated budget {budget.id}")
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    *,
    db: Session = Depends(deps.get_db),
    budget: models.Budget = Depends(deps.get_user_budget),
):
    """Delete a budget"""
    logger.info(f"User {budget.user_id} is deleting budget {budget.id}")
    crud.budget.remove(db, id=budget.id)
    logger.info(f"User {budget.user_id} successfully deleted budget {budget.id}")
    return None
