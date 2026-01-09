from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.post("/", response_model=schemas.BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    *,
    db: Session = Depends(deps.get_db),
    budget_in: schemas.BudgetCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    # If category_id provided, verify it exists and belongs to user or is system category
    if budget_in.category_id:
        category = crud.category.get(db, id=budget_in.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        if category.user_id and category.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Cannot set budget for another user's category"
            )

    budget = crud.budget.create(db, obj_in=budget_in, user_id=current_user.id)
    return budget


@router.get("/month", response_model=List[schemas.BudgetWithCategory])
def get_monthly_budgets(
    *,
    db: Session = Depends(deps.get_db),
    year: int,
    month: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
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
    db: Session = Depends(deps.get_db),
    budget_id: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """Get a specific budget by ID"""
    budget = crud.budget.get(db, id=budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this budget"
        )
    return budget


@router.put("/{budget_id}", response_model=schemas.BudgetResponse)
def update_budget(
    *,
    db: Session = Depends(deps.get_db),
    budget_id: int,
    budget_in: schemas.BudgetUpdate,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """Update a budget amount"""
    budget = crud.budget.get(db, id=budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this budget"
        )

    budget = crud.budget.update(db, db_obj=budget, obj_in=budget_in)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    *,
    db: Session = Depends(deps.get_db),
    budget_id: int,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """Delete a budget"""
    budget = crud.budget.get(db, id=budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this budget"
        )

    crud.budget.remove(db, id=budget_id)
    return None
