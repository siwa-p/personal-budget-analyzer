from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CRUDCategory:
    def get(self, db: Session, id: int) -> Optional[Category]:
        return db.query(Category).filter(Category.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Category]:
        return db.query(Category).offset(skip).limit(limit).all()

    def get_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Category]:
        """Get categories for a specific user, including system categories (user_id=None)"""
        return (
            db.query(Category)
            .filter((Category.user_id == user_id) | (Category.user_id == None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_system_categories(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Category]:
        """Get only system categories (user_id=None)"""
        return db.query(Category).filter(Category.user_id == None).offset(skip).limit(limit).all()

    def get_by_name_and_user(
        self, db: Session, *, name: str, type: str, user_id: Optional[int]
    ) -> Optional[Category]:
        """Check if a category with this name and type already exists for this user"""
        return (
            db.query(Category)
            .filter(Category.name == name, Category.type == type, Category.user_id == user_id)
            .first()
        )

    def create(self, db: Session, *, obj_in: CategoryCreate, user_id: Optional[int]) -> Category:
        db_obj = Category(
            name=obj_in.name,
            type=obj_in.type,
            user_id=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Category, obj_in: Union[CategoryUpdate, Dict[str, Any]]) -> Category:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Category:
        obj = db.get(Category, id)
        db.delete(obj)
        db.commit()
        return obj


category = CRUDCategory()
