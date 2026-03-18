from datetime import date, datetime
from typing import Annotated
import csv
import io

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app import crud, schemas
from app.api import deps
from app.api.deps import CurrentUser, DbSession, UserTransaction
from app.core.logger_init import setup_logging
from app.services.ml_service import incremental_update as ml_incremental_update
from app.services.ml_service import predict_category as ml_predict_category

logger = setup_logging()
router = APIRouter()

_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d/%m/%Y"]


def _parse_date_iso(s: str) -> str | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


@router.get("/", response_model=list[schemas.TransactionRead])
def read_transactions(
    *,
    db: DbSession,
    skip: int = 0,
    limit: int = 100,
    category_id: int | None = None,
    transaction_type: str | None = Query(default=None, pattern="^(income|expense)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: CurrentUser,
) -> list[schemas.TransactionRead]:
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


@router.get("/export", response_class=StreamingResponse)
def export_transactions(
    *,
    db: DbSession,
    category_id: int | None = None,
    transaction_type: str | None = Query(default=None, pattern="^(income|expense)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: CurrentUser,
) -> StreamingResponse:
    logger.info(
        f"User {current_user.id} is exporting transactions with filters - "
        f"category_id: {category_id}, transaction_type: {transaction_type}, "
        f"start_date: {start_date}, end_date: {end_date}"
    )

    transactions = crud.transaction.get_filtered_for_export(
        db,
        user_id=current_user.id,
        category_id=category_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
    )

    def iter_csv() -> list[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Header row
        writer.writerow(
            [
                "id",
                "date",
                "description",
                "category_id",
                "transaction_type",
                "amount",
                "account_name",
                "bill_id",
                "goal_id",
            ]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for txn in transactions:
            writer.writerow(
                [
                    txn.id,
                    txn.transaction_date.isoformat() if txn.transaction_date else "",
                    txn.description or "",
                    txn.category_id,
                    txn.transaction_type,
                    f"{txn.amount:.2f}" if txn.amount is not None else "",
                    txn.account_name or "",
                    txn.bill_id or "",
                    txn.goal_id or "",
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.post("/", response_model=schemas.TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    *,
    db: DbSession,
    transaction_in: schemas.TransactionCreate,
    current_user: CurrentUser,
) -> schemas.TransactionRead:
    logger.info(
        f"User {current_user.id} is creating a new transaction - "
        f"amount: ${transaction_in.amount}, type: {transaction_in.transaction_type}, "
        f"category_id: {transaction_in.category_id}, goal_id: {transaction_in.goal_id}"
    )

    # Validate category access
    deps.validate_category_access(db, transaction_in.category_id, current_user.id)

    # Validate goal access and check amount limits
    if transaction_in.goal_id:
        goal = deps.validate_goal_access(db, transaction_in.goal_id, current_user.id)

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


@router.get("/suggest-category")
def suggest_category(
    *,
    db: DbSession,
    description: str,
    current_user: CurrentUser,
) -> dict:
    """Return the most likely category for a transaction description."""
    if len(description.strip()) < 3:
        return {"category_id": None, "category_name": None, "confidence": 0.0, "source": "none"}

    all_cats = crud.category.get_by_user(db, user_id=current_user.id)
    available = [{"id": c.id, "name": c.name, "type": c.type} for c in all_cats]
    return ml_predict_category(db, current_user.id, description.strip(), available)


@router.post("/feedback", response_model=schemas.CategoryFeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_category_feedback(
    *,
    db: DbSession,
    feedback_in: schemas.CategoryFeedbackCreate,
    current_user: CurrentUser,
) -> schemas.CategoryFeedbackRead:
    """Record whether the user accepted or overrode a category suggestion."""
    feedback = crud.category_feedback.create(db, obj_in=feedback_in, user_id=current_user.id)

    chosen_cat = crud.category.get(db, id=feedback_in.chosen_category_id)
    chosen_name = chosen_cat.name if chosen_cat else f"id={feedback_in.chosen_category_id}"
    if feedback.is_correction:
        suggested_cat = crud.category.get(db, id=feedback_in.suggested_category_id) if feedback_in.suggested_category_id else None
        suggested_name = suggested_cat.name if suggested_cat else "none"
        logger.info(
            f"[training sample] User {current_user.id}: CORRECTION "
            f"'{feedback_in.description}' → '{chosen_name}' (was suggested '{suggested_name}', "
            f"source={feedback.source!r}, confidence={feedback_in.confidence}) — weight x3 in training"
        )
    else:
        logger.info(
            f"[training sample] User {current_user.id}: ACCEPTED "
            f"'{feedback_in.description}' → '{chosen_name}' "
            f"(source={feedback.source!r}, confidence={feedback_in.confidence})"
        )

    ml_incremental_update(current_user.id, feedback_in.description, chosen_name, is_correction=feedback.is_correction)

    return schemas.CategoryFeedbackRead.model_validate(feedback)


@router.post("/scan-receipt", status_code=status.HTTP_200_OK)
def scan_receipt(
    *,
    file: Annotated[UploadFile, File()],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Extract transaction fields from a receipt image. Does not save a transaction."""
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Only JPEG, PNG, or WebP images accepted")

    image_bytes = file.file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="Image too large (max 10 MB)")

    try:
        from app.services.ocr_service import scan_receipt as ocr_scan
        extracted = ocr_scan(image_bytes)
    except Exception as err:
        logger.exception("Receipt scan failed")
        raise HTTPException(status_code=500, detail="Receipt scanning failed") from err

    suggestion = None
    if extracted.get("description"):
        categories = crud.category.get_by_user(db, user_id=current_user.id)
        available = [{"id": c.id, "name": c.name} for c in categories]
        suggestion = ml_predict_category(db, current_user.id, extracted["description"], available)

    dates = extracted.get("dates", [])
    date_iso = next((d for s in dates if (d := _parse_date_iso(s))), None)

    return {
        "amount": extracted.get("amount"),
        "description": extracted.get("description"),
        "date": date_iso,
        "total_validated": extracted.get("total_validated"),
        "category_suggestion": suggestion,
    }


@router.get("/{transaction_id}", response_model=schemas.TransactionRead)
def read_transaction(
    *,
    transaction: UserTransaction,
) -> schemas.TransactionRead:
    return schemas.TransactionRead.model_validate(transaction)


@router.put("/{transaction_id}", response_model=schemas.TransactionRead)
def update_transaction(
    *,
    db: DbSession,
    transaction: UserTransaction,
    transaction_in: schemas.TransactionUpdate,
) -> schemas.TransactionRead:
    logger.info(f"User {transaction.user_id} is updating transaction {transaction.id}")

    # Validate new category if provided
    if transaction_in.category_id:
        deps.validate_category_access(db, transaction_in.category_id, transaction.user_id)

    # Validate goal and amount limits
    if transaction_in.goal_id is not None or transaction_in.amount is not None:
        goal_id_to_check = transaction_in.goal_id if transaction_in.goal_id is not None else transaction.goal_id

        if goal_id_to_check:
            goal = deps.validate_goal_access(db, goal_id_to_check, transaction.user_id)

            progress = crud.goal.calculate_progress(db, goal_id=goal_id_to_check)
            if transaction.goal_id == goal_id_to_check:
                progress["current_amount"] -= transaction.amount

            new_amount = transaction_in.amount if transaction_in.amount is not None else transaction.amount
            new_total = progress["current_amount"] + new_amount

            if new_total > goal.target_amount:
                logger.warning(
                    f"User {transaction.user_id} attempted to update transaction {transaction.id} "
                    f"which would exceed goal {goal_id_to_check} target - "
                    f"Would be: ${new_total:.2f}, Target: ${goal.target_amount:.2f}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Updated transaction would exceed goal target. Current: ${progress['current_amount']:.2f}, "
                    f"New amount: ${new_amount:.2f}, Target: ${goal.target_amount:.2f}",
                )

            logger.info(
                f"User {transaction.user_id} updating transaction {transaction.id} with goal {goal_id_to_check} - "
                f"New progress will be: ${new_total:.2f}/{goal.target_amount:.2f}"
            )

    transaction = crud.transaction.update(db, db_obj=transaction, obj_in=transaction_in)
    logger.info(f"User {transaction.user_id} successfully updated transaction {transaction.id}")
    return schemas.TransactionRead.model_validate(transaction)


@router.delete("/{transaction_id}", response_model=schemas.TransactionRead)
def delete_transaction(
    *,
    db: DbSession,
    transaction: UserTransaction,
) -> schemas.TransactionRead:
    logger.info(f"User {transaction.user_id} is deleting transaction {transaction.id}")

    if transaction.goal_id:
        logger.info(
            f"User {transaction.user_id} deleting transaction {transaction.id} that was linked to goal {transaction.goal_id} - "
            f"Goal progress will be reduced by ${transaction.amount:.2f}"
        )

    deleted_transaction = crud.transaction.remove(db, id=transaction.id)
    logger.info(f"User {transaction.user_id} successfully deleted transaction {transaction.id}")
    return schemas.TransactionRead.model_validate(deleted_transaction)
