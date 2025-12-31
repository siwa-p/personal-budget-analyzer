from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.TransactionRead])
def read_transactions(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = Query(default=None, pattern="^(income|expense)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.TransactionRead]:
    """Get transactions with optional filters"""
    # Apply filters based on query parameters
    if start_date and end_date:
        transactions = crud.transaction.get_by_date_range(
            db, user_id=current_user.id, start_date=start_date, end_date=end_date, skip=skip, limit=limit
        )
    elif category_id:
        transactions = crud.transaction.get_by_category(
            db, user_id=current_user.id, category_id=category_id, skip=skip, limit=limit
        )
    elif transaction_type:
        transactions = crud.transaction.get_by_type(
            db, user_id=current_user.id, transaction_type=transaction_type, skip=skip, limit=limit
        )
    else:
        transactions = crud.transaction.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)

    return [schemas.TransactionRead.model_validate(txn) for txn in transactions]


@router.post("/", response_model=schemas.TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    *,
    db: Session = Depends(deps.get_db),
    transaction_in: schemas.TransactionCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.TransactionRead:
    """Create a new transaction"""
    # Verify category exists and user has access to it
    category = crud.category.get(db, id=transaction_in.category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Check if user has access to category (own category or system category)
    if category.user_id and category.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this category")

    transaction = crud.transaction.create(db, obj_in=transaction_in, user_id=current_user.id)
    return schemas.TransactionRead.model_validate(transaction)


@router.get("/{transaction_id}", response_model=schemas.TransactionRead)
def read_transaction(
    *,
    db: Session = Depends(deps.get_db),
    transaction_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.TransactionRead:
    """Get transaction by ID"""
    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Only allow access to own transactions
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this transaction")

    return schemas.TransactionRead.model_validate(transaction)


@router.put("/{transaction_id}", response_model=schemas.TransactionRead)
def update_transaction(
    *,
    db: Session = Depends(deps.get_db),
    transaction_id: int,
    transaction_in: schemas.TransactionUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.TransactionRead:
    """Update a transaction"""
    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Only allow updating own transactions
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this transaction")

    # If updating category, verify access
    if transaction_in.category_id:
        category = crud.category.get(db, id=transaction_in.category_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        if category.user_id and category.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this category")

    transaction = crud.transaction.update(db, db_obj=transaction, obj_in=transaction_in)
    return schemas.TransactionRead.model_validate(transaction)


@router.delete("/{transaction_id}", response_model=schemas.TransactionRead)
def delete_transaction(
    *,
    db: Session = Depends(deps.get_db),
    transaction_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.TransactionRead:
    """Delete a transaction"""
    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Only allow deleting own transactions
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this transaction")

    transaction = crud.transaction.remove(db, id=transaction_id)
    return schemas.TransactionRead.model_validate(transaction)
