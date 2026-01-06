from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.logger_init import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/", response_model=List[schemas.BillRead])
def read_bills(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.BillRead]:
    logger.info(f"User {current_user.id} is retrieving bills")
    bills = crud.bill.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return [schemas.BillRead.model_validate(bill) for bill in bills]


@router.post("/", response_model=schemas.BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill_in: schemas.BillCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.BillRead:
    logger.info(
        f"User {current_user.id} is creating a new bill - "
        f"title: {bill_in.title}, amount: ${bill_in.amount}, due_date: {bill_in.due_date}"
    )

    existing_bill = crud.bill.get_by_title_date_and_user(
        db, title=bill_in.title, due_date=bill_in.due_date, user_id=current_user.id
    )
    if existing_bill:
        logger.warning(
            f"User {current_user.id} attempted to create duplicate bill - "
            f"title: {bill_in.title}, due_date: {bill_in.due_date}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bill '{bill_in.title}' with due date {bill_in.due_date} already exists",
        )

    bill = crud.bill.create(db, obj_in=bill_in, user_id=current_user.id)
    logger.info(f"User {current_user.id} successfully created bill {bill.id}")
    return schemas.BillRead.model_validate(bill)


@router.get("/{bill_id}", response_model=schemas.BillRead)
def read_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.BillRead:
    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        logger.warning(f"User {current_user.id} attempted to access non-existent bill {bill_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    if bill.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to bill {bill_id}")
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
    logger.info(f"User {current_user.id} is updating bill {bill_id}")

    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        logger.warning(f"User {current_user.id} attempted to update non-existent bill {bill_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    if bill.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized update of bill {bill_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this bill")

    bill = crud.bill.update(db, db_obj=bill, obj_in=bill_in)
    logger.info(f"User {current_user.id} successfully updated bill {bill_id}")
    return schemas.BillRead.model_validate(bill)


@router.delete("/{bill_id}", response_model=schemas.BillRead)
def delete_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.BillRead:
    logger.info(f"User {current_user.id} is deleting bill {bill_id}")

    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        logger.warning(f"User {current_user.id} attempted to delete non-existent bill {bill_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    if bill.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized deletion of bill {bill_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this bill")

    bill = crud.bill.remove(db, id=bill_id)
    logger.info(f"User {current_user.id} successfully deleted bill {bill_id}")
    return schemas.BillRead.model_validate(bill)
