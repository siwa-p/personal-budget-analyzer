from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryUpdate]):
    def __init__(self):
        super().__init__(Category)

    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100, include_inactive: bool = False
    ) -> list[Category]:
        """Get categories for a specific user, including system categories (user_id=None)"""
        stmt = select(Category).where((Category.user_id == user_id) | (Category.user_id == None))

        if not include_inactive:
            stmt = stmt.where(Category.is_active)

        stmt = stmt.offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def get_system_categories(
        self, db: Session, *, skip: int = 0, limit: int = 100, include_inactive: bool = False
    ) -> list[Category]:
        """Get only system categories (user_id=None)"""
        stmt = select(Category).where(Category.user_id == None)

        if not include_inactive:
            stmt = stmt.where(Category.is_active)

        stmt = stmt.offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def get_by_name_and_user(
        self, db: Session, *, name: str, type: str, user_id: int | None
    ) -> Category | None:
        """Check if a category with this name and type already exists for this user"""
        stmt = select(Category).where(
            Category.name == name,
            Category.type == type,
            Category.user_id == user_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def create(self, db: Session, *, obj_in: CategoryCreate, user_id:int | None) -> Category:
        db_obj = Category(
            name=obj_in.name,
            type=obj_in.type,
            description=obj_in.description,
            icon=obj_in.icon,
            color=obj_in.color,
            parent_category_id=obj_in.parent_category_id,
            user_id=user_id,
            is_active=True,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def soft_delete(self, db: Session, *, id: int) -> Category:
        """Soft delete by setting is_active to False"""
        obj = db.get(Category, id)
        obj.is_active = False
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj


category = CRUDCategory()
