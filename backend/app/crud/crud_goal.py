from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from app.models.goal import Goal
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

    def create(self, db: Session, *, obj_in: GoalCreate) -> Goal:
        db_obj = Goal(
            user_id=obj_in.user_id,
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


goal = CRUDGoal()
