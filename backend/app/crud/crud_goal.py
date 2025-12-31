from typing import Any, Dict, List, Optional, Union

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.transaction import Transactions
from app.schemas.goal import GoalCreate, GoalUpdate


class CRUDGoal:
    def get(self, db: Session, id: int) -> Optional[Goal]:
        return db.query(Goal).filter(Goal.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Goal]:
        return db.query(Goal).offset(skip).limit(limit).all()

    def get_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Goal]:
        return db.query(Goal).filter(Goal.user_id == user_id).offset(skip).limit(limit).all()

    def get_by_status(
        self, db: Session, *, user_id: int, status: str, skip: int = 0, limit: int = 100
    ) -> List[Goal]:
        return (
            db.query(Goal)
            .filter(Goal.user_id == user_id, Goal.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, *, obj_in: GoalCreate, user_id: int) -> Goal:
        db_obj = Goal(
            user_id=user_id,
            name=obj_in.name,
            target_amount=obj_in.target_amount,
            deadline=obj_in.deadline,
            status=obj_in.status,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Goal, obj_in: Union[GoalUpdate, Dict[str, Any]]) -> Goal:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Goal:
        obj = db.get(Goal, id)
        db.delete(obj)
        db.commit()
        return obj

    def calculate_progress(self, db: Session, *, goal_id: int) -> Dict[str, float]:
        """Calculate progress for a goal based on linked transactions"""
        # Sum all transaction amounts linked to this goal
        result = (
            db.query(func.sum(Transactions.amount))
            .filter(Transactions.goal_id == goal_id)
            .scalar()
        )

        current_amount = float(result) if result else 0.0

        # Get the goal to calculate percentage
        goal = self.get(db, id=goal_id)
        if not goal:
            return {"current_amount": 0.0, "progress_percentage": 0.0, "remaining_amount": 0.0}

        target_amount = float(goal.target_amount)
        progress_percentage = (current_amount / target_amount * 100) if target_amount > 0 else 0.0
        remaining_amount = max(0.0, target_amount - current_amount)

        return {
            "current_amount": current_amount,
            "progress_percentage": min(100.0, progress_percentage),  # Cap at 100%
            "remaining_amount": remaining_amount,
        }


goal = CRUDGoal()
