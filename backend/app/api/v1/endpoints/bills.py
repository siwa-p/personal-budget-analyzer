from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.BillRead])
def read_bills(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.BillRead]:
    """Get all bills for the current user"""
    bills = crud.bill.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return [schemas.BillRead.model_validate(bill) for bill in bills]


@router.post("/", response_model=schemas.BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill_in: schemas.BillCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.BillRead:
    """Create a new bill"""
    # Force user_id to current user
    bill_in.user_id = current_user.id
    bill = crud.bill.create(db, obj_in=bill_in)
    return schemas.BillRead.model_validate(bill)


@router.get("/{bill_id}", response_model=schemas.BillRead)
def read_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.BillRead:
    """Get bill by ID"""
    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Only allow access to own bills
    if bill.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this bill")

    return schemas.BillRead.model_validate(bill)


@router.put("/{bill_id}", response_model=schemas.BillRead)
def update_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill_id: int,
    bill_in: schemas.BillUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.BillRead:
    """Update a bill"""
    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Only allow updating own bills
    if bill.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this bill")

    bill = crud.bill.update(db, db_obj=bill, obj_in=bill_in)
    return schemas.BillRead.model_validate(bill)


@router.delete("/{bill_id}", response_model=schemas.BillRead)
def delete_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.BillRead:
    """Delete a bill"""
    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Only allow deleting own bills
    if bill.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this bill")

    bill = crud.bill.remove(db, id=bill_id)
    return schemas.BillRead.model_validate(bill)
