from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.schemas.bill import BillCreate, BillUpdate


class CRUDBill:
    def get(self, db: Session, id: int) -> Optional[Bill]:
        return db.query(Bill).filter(Bill.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Bill]:
        return db.query(Bill).offset(skip).limit(limit).all()

    def get_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Bill]:
        return db.query(Bill).filter(Bill.user_id == user_id).offset(skip).limit(limit).all()

    def get_by_title_date_and_user(self, db: Session, *, title: str, due_date, user_id: int) -> Optional[Bill]:
        """Check if a bill with this title and due date already exists for this user"""
        return db.query(Bill).filter(Bill.title == title, Bill.due_date == due_date, Bill.user_id == user_id).first()

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


bill = CRUDBill()
