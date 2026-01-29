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
    bill: models.Bill = Depends(deps.get_user_bill),
) -> schemas.BillRead:
    return schemas.BillRead.model_validate(bill)


@router.put("/{bill_id}", response_model=schemas.BillRead)
def update_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill: models.Bill = Depends(deps.get_user_bill),
    bill_in: schemas.BillUpdate,
) -> schemas.BillRead:
    logger.info(f"User {bill.user_id} is updating bill {bill.id}")
    bill = crud.bill.update(db, db_obj=bill, obj_in=bill_in)
    logger.info(f"User {bill.user_id} successfully updated bill {bill.id}")
    return schemas.BillRead.model_validate(bill)


@router.delete("/{bill_id}", response_model=schemas.BillRead)
def delete_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill: models.Bill = Depends(deps.get_user_bill),
) -> schemas.BillRead:
    logger.info(f"User {bill.user_id} is deleting bill {bill.id}")
    deleted_bill = crud.bill.remove(db, id=bill.id)
    logger.info(f"User {bill.user_id} successfully deleted bill {bill.id}")
    return schemas.BillRead.model_validate(deleted_bill)


@router.get("/upcoming/", response_model=List[schemas.BillRead])
def read_upcoming_bills(
    *,
    db: Session = Depends(deps.get_db),
    days_ahead: int = 7,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.BillRead]:
    """Retrieve bills due in the next 'days_ahead' days"""
    logger.info(f"User {current_user.id} is retrieving bills due in the next {days_ahead} days")
    bills = crud.bill.get_upcoming_bills(
        db, user_id=current_user.id, days_ahead=days_ahead
    )
    return [schemas.BillRead.model_validate(bill) for bill in bills]


@router.get("/overdue/", response_model=List[schemas.BillRead])
def read_overdue_bills(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.BillRead]:
    """Retrieve bills that are overdue"""
    logger.info(f"User {current_user.id} is retrieving overdue bills")
    bills = crud.bill.get_overdue_bills(
        db, user_id=current_user.id
    )
    return [schemas.BillRead.model_validate(bill) for bill in bills]


@router.post("/{bill_id}/mark-paid", response_model=schemas.BillRead)
def mark_bill_as_paid(
    *,
    db: Session = Depends(deps.get_db),
    bill: models.Bill = Depends(deps.get_user_bill),
) -> schemas.BillRead:
    """Mark a bill as paid by updating its last_paid_date to today.
    If the bill is recurring, automatically updates the due_date to the next occurrence."""
    logger.info(f"User {bill.user_id} is marking bill {bill.id} as paid")

    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    update_data = {"last_paid_date": datetime.now().date()}

    # If the bill is recurring, calculate the next due date
    if bill.recurrence != "none":
        if bill.recurrence == "daily":
            next_due_date = bill.due_date + relativedelta(days=1)
        elif bill.recurrence == "weekly":
            next_due_date = bill.due_date + relativedelta(weeks=1)
        elif bill.recurrence == "monthly":
            next_due_date = bill.due_date + relativedelta(months=1)
        elif bill.recurrence == "yearly":
            next_due_date = bill.due_date + relativedelta(years=1)
        else:
            logger.error(f"Bill {bill.id} has invalid recurrence pattern: {bill.recurrence}")
            next_due_date = None

        if next_due_date:
            update_data["due_date"] = next_due_date
            logger.info(f"Recurring bill {bill.id}: updating next due date to {next_due_date}")

    bill_in = schemas.BillUpdate(**update_data)
    bill = crud.bill.update(db, db_obj=bill, obj_in=bill_in)
    logger.info(f"User {bill.user_id} successfully marked bill {bill.id} as paid")
    return schemas.BillRead.model_validate(bill)


@router.post("/{bill_id}/next-due", response_model=schemas.BillRead)
def get_next_due_bill(
    *,
    db: Session = Depends(deps.get_db),
    bill: models.Bill = Depends(deps.get_user_bill),
) -> schemas.BillRead:
    """Get the next due date for a recurring bill"""
    logger.info(f"User {bill.user_id} is retrieving next due date for bill {bill.id}")

    if bill.recurrence == "none":
        logger.info(f"Bill {bill.id} is not recurring; no next due date")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill is not recurring")

    from dateutil.relativedelta import relativedelta

    if bill.recurrence == "daily":
        next_due_date = bill.due_date + relativedelta(days=1)
    elif bill.recurrence == "weekly":
        next_due_date = bill.due_date + relativedelta(weeks=1)
    elif bill.recurrence == "monthly":
        next_due_date = bill.due_date + relativedelta(months=1)
    elif bill.recurrence == "yearly":
        next_due_date = bill.due_date + relativedelta(years=1)
    else:
        logger.error(f"Bill {bill.id} has invalid recurrence pattern: {bill.recurrence}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid recurrence pattern")

    bill_in = schemas.BillUpdate(due_date=next_due_date)
    bill = crud.bill.update(db, db_obj=bill, obj_in=bill_in)
    logger.info(f"User {bill.user_id} successfully updated next due date for bill {bill.id} to {next_due_date}")
    return schemas.BillRead.model_validate(bill)
