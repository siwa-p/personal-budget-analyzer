from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.schemas.bill import BillCreate, BillUpdate


class CRUDBill:
    def get(self, db: Session, id: int) -> Optional[Bill]:
        stmt = select(Bill).where(Bill.id == id)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Bill]:
        stmt = select(Bill).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def get_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Bill]:
        stmt = select(Bill).where(Bill.user_id == user_id).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def get_by_title_date_and_user(self, db: Session, *, title: str, due_date, user_id: int) -> Optional[Bill]:
        """Check if a bill with this title and due date already exists for this user"""
        stmt = select(Bill).where(Bill.title == title, Bill.due_date == due_date, Bill.user_id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    def create(self, db: Session, *, obj_in: BillCreate, user_id: int) -> Bill:
        db_obj = Bill(
            user_id=user_id,
            title=obj_in.title,
            amount=obj_in.amount,
            due_date=obj_in.due_date,
            recurrence=obj_in.recurrence,
            last_paid_date=obj_in.last_paid_date,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Bill, obj_in: Union[BillUpdate, Dict[str, Any]]) -> Bill:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Bill:
        obj = db.get(Bill, id)
        db.delete(obj)
        db.commit()
        return obj

    def get_upcoming_bills(self, db: Session, *, user_id: int, days_ahead: int = 7) -> List[Bill]:
        from datetime import datetime, timedelta

        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)

        stmt = select(Bill).where(
            Bill.user_id == user_id,
            Bill.due_date >= today,
            Bill.due_date <= end_date
        ).order_by(Bill.due_date)

        return list(db.execute(stmt).scalars().all())
    
    def get_overdue_bills(self, db: Session, *, user_id: int) -> List[Bill]:
        from datetime import datetime

        today = datetime.now().date()

        stmt = select(Bill).where(
            Bill.user_id == user_id,
            Bill.due_date < today
        ).order_by(Bill.due_date)

        return list(db.execute(stmt).scalars().all())

bill = CRUDBill()
