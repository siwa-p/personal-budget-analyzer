from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from app.models.goal_transaction import GoalTransaction
from app.schemas.goal_transaction import GoalTransactionCreate


class CRUDGoalTransaction:
    def get(self, db: Session, id: int) -> Optional[GoalTransaction]:
        return db.query(GoalTransaction).filter(GoalTransaction.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[GoalTransaction]:
        return db.query(GoalTransaction).offset(skip).limit(limit).all()

    def get_by_goal(
        self, db: Session, *, goal_id: int, skip: int = 0, limit: int = 100
    ) -> List[GoalTransaction]:
        return (
            db.query(GoalTransaction)
            .filter(GoalTransaction.goal_id == goal_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_transaction(
        self, db: Session, *, transaction_id: int, skip: int = 0, limit: int = 100
    ) -> List[GoalTransaction]:
        return (
            db.query(GoalTransaction)
            .filter(GoalTransaction.transaction_id == transaction_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, *, obj_in: GoalTransactionCreate) -> GoalTransaction:
        db_obj = GoalTransaction(
            goal_id=obj_in.goal_id,
            transaction_id=obj_in.transaction_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> GoalTransaction:
        obj = db.get(GoalTransaction, id)
        db.delete(obj)
        db.commit()
        return obj


goal_transaction = CRUDGoalTransaction()
