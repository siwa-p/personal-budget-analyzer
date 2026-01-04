from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser:
    def get(self, db: Session, id: int) -> Optional[User]:
        stmt = select(User).where(User.id == id)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[User]:
        stmt = select(User).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email.lower(),
            username=obj_in.username,
            full_name=obj_in.full_name,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]) -> User:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        password = update_data.pop("password", None)
        if password:
            update_data["hashed_password"] = get_password_hash(password)

        email = update_data.get("email")
        if email:
            update_data["email"] = email.lower()

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> User:
        obj = db.get(User, id)
        db.delete(obj)
        db.commit()
        return obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return bool(user.is_active)

    def is_superuser(self, user: User) -> bool:
        return bool(user.is_superuser)


user = CRUDUser()
