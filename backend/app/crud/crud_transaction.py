from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.transaction import Transactions
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class CRUDTransaction(CRUDBase[Transactions, TransactionCreate, TransactionUpdate]):
    def __init__(self):
        super().__init__(Transactions)

    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Transactions]:
        stmt = (
            select(Transactions)
            .where(Transactions.user_id == user_id)
            .order_by(Transactions.transaction_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def get_by_category(
        self, db: Session, *, user_id: int, category_id: int, skip: int = 0, limit: int = 100
    ) -> list[Transactions]:
        stmt = (
            select(Transactions)
            .where(Transactions.user_id == user_id, Transactions.category_id == category_id)
            .order_by(Transactions.transaction_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def get_by_date_range(
        self,
        db: Session,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transactions]:
        stmt = (
            select(Transactions)
            .where(
                Transactions.user_id == user_id,
                Transactions.transaction_date >= start_date,
                Transactions.transaction_date <= end_date,
            )
            .order_by(Transactions.transaction_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def get_by_type(
        self, db: Session, *, user_id: int, transaction_type: str, skip: int = 0, limit: int = 100
    ) -> list[Transactions]:
        stmt = (
            select(Transactions)
            .where(Transactions.user_id == user_id, Transactions.transaction_type == transaction_type)
            .order_by(Transactions.transaction_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, *, obj_in: TransactionCreate, user_id: int) -> Transactions:
        db_obj = Transactions(
            user_id=user_id,
            category_id=obj_in.category_id,
            amount=obj_in.amount,
            description=obj_in.description,
            transaction_date=obj_in.transaction_date,
            transaction_type=obj_in.transaction_type,
            account_name=obj_in.account_name,
            bill_id=obj_in.bill_id,
            goal_id=obj_in.goal_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


transaction = CRUDTransaction()
