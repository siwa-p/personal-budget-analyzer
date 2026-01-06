from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.logger_init import setup_logging

logger = setup_logging()
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
    logger.info(
        f"User {current_user.id} is retrieving transactions with filters - "
        f"category_id: {category_id}, transaction_type: {transaction_type}"
    )

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
    logger.info(
        f"User {current_user.id} is creating a new transaction - "
        f"amount: ${transaction_in.amount}, type: {transaction_in.transaction_type}, "
        f"category_id: {transaction_in.category_id}, goal_id: {transaction_in.goal_id}"
    )

    category = crud.category.get(db, id=transaction_in.category_id)
    if not category:
        logger.warning(f"User {current_user.id} attempted to use non-existent category {transaction_in.category_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category.user_id and category.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to category {transaction_in.category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this category")

    if transaction_in.goal_id:
        goal = crud.goal.get(db, id=transaction_in.goal_id)
        if not goal:
            logger.warning(f"User {current_user.id} attempted to link to non-existent goal {transaction_in.goal_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

        if goal.user_id != current_user.id:
            logger.warning(f"User {current_user.id} attempted unauthorized access to goal {transaction_in.goal_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this goal")

        progress = crud.goal.calculate_progress(db, goal_id=transaction_in.goal_id)
        new_total = progress["current_amount"] + transaction_in.amount

        if new_total > goal.target_amount:
            logger.warning(
                f"User {current_user.id} attempted to exceed goal {transaction_in.goal_id} target - "
                f"Current: ${progress['current_amount']:.2f}, Adding: ${transaction_in.amount:.2f}, "
                f"Target: ${goal.target_amount:.2f}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction amount would exceed goal target. Current: ${progress['current_amount']:.2f}, "
                f"Adding: ${transaction_in.amount:.2f}, Target: ${goal.target_amount:.2f}, "
                f"Remaining: ${progress['remaining_amount']:.2f}",
            )

        logger.info(
            f"User {current_user.id} linking transaction to goal {transaction_in.goal_id} - "
            f"Progress will be: ${new_total:.2f}/{goal.target_amount:.2f} "
            f"({(new_total/goal.target_amount)*100:.1f}%)"
        )

    transaction = crud.transaction.create(db, obj_in=transaction_in, user_id=current_user.id)
    logger.info(f"User {current_user.id} successfully created transaction {transaction.id}")
    return schemas.TransactionRead.model_validate(transaction)


@router.get("/{transaction_id}", response_model=schemas.TransactionRead)
def read_transaction(
    *,
    db: Session = Depends(deps.get_db),
    transaction_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.TransactionRead:
    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this transaction"
        )

    return schemas.TransactionRead.model_validate(transaction)


@router.put("/{transaction_id}", response_model=schemas.TransactionRead)
def update_transaction(
    *,
    db: Session = Depends(deps.get_db),
    transaction_id: int,
    transaction_in: schemas.TransactionUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.TransactionRead:
    logger.info(f"User {current_user.id} is updating transaction {transaction_id}")

    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        logger.warning(f"User {current_user.id} attempted to update non-existent transaction {transaction_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if transaction.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized update of transaction {transaction_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this transaction"
        )

    if transaction_in.category_id:
        category = crud.category.get(db, id=transaction_in.category_id)
        if not category:
            logger.warning(
                f"User {current_user.id} attempted to update transaction {transaction_id} "
                f"with non-existent category {transaction_in.category_id}"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        if category.user_id and category.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted unauthorized category access while updating transaction {transaction_id}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this category")

    if transaction_in.goal_id is not None or transaction_in.amount is not None:
        goal_id_to_check = transaction_in.goal_id if transaction_in.goal_id is not None else transaction.goal_id

        if goal_id_to_check:
            goal = crud.goal.get(db, id=goal_id_to_check)
            if not goal:
                logger.warning(
                    f"User {current_user.id} attempted to link transaction {transaction_id} "
                    f"to non-existent goal {goal_id_to_check}"
                )
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

            if goal.user_id != current_user.id:
                logger.warning(
                    f"User {current_user.id} attempted unauthorized goal access while updating transaction {transaction_id}"
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this goal")

            progress = crud.goal.calculate_progress(db, goal_id=goal_id_to_check)
            if transaction.goal_id == goal_id_to_check:
                progress["current_amount"] -= transaction.amount

            new_amount = transaction_in.amount if transaction_in.amount is not None else transaction.amount
            new_total = progress["current_amount"] + new_amount

            if new_total > goal.target_amount:
                logger.warning(
                    f"User {current_user.id} attempted to update transaction {transaction_id} "
                    f"which would exceed goal {goal_id_to_check} target - "
                    f"Would be: ${new_total:.2f}, Target: ${goal.target_amount:.2f}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Updated transaction would exceed goal target. Current: ${progress['current_amount']:.2f}, "
                    f"New amount: ${new_amount:.2f}, Target: ${goal.target_amount:.2f}",
                )

            logger.info(
                f"User {current_user.id} updating transaction {transaction_id} with goal {goal_id_to_check} - "
                f"New progress will be: ${new_total:.2f}/{goal.target_amount:.2f}"
            )

    transaction = crud.transaction.update(db, db_obj=transaction, obj_in=transaction_in)
    logger.info(f"User {current_user.id} successfully updated transaction {transaction_id}")
    return schemas.TransactionRead.model_validate(transaction)


@router.delete("/{transaction_id}", response_model=schemas.TransactionRead)
def delete_transaction(
    *,
    db: Session = Depends(deps.get_db),
    transaction_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.TransactionRead:
    logger.info(f"User {current_user.id} is deleting transaction {transaction_id}")

    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        logger.warning(f"User {current_user.id} attempted to delete non-existent transaction {transaction_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if transaction.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized deletion of transaction {transaction_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this transaction"
        )

    if transaction.goal_id:
        logger.info(
            f"User {current_user.id} deleting transaction {transaction_id} that was linked to goal {transaction.goal_id} - "
            f"Goal progress will be reduced by ${transaction.amount:.2f}"
        )

    transaction = crud.transaction.remove(db, id=transaction_id)
    logger.info(f"User {current_user.id} successfully deleted transaction {transaction_id}")
    return schemas.TransactionRead.model_validate(transaction)
