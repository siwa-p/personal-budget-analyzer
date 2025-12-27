from contextlib import contextmanager
from typing import Iterator

from app import crud, schemas
from app.core.config import settings
from app.db.session import SessionLocal
from sqlalchemy.orm import Session


@contextmanager
def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_superuser() -> None:
    email = settings.FIRST_SUPERUSER_EMAIL
    password = settings.FIRST_SUPERUSER_PASSWORD
    username = settings.FIRST_SUPERUSER_USERNAME

    if not email or not password or not username:
        raise ValueError("Superuser credentials are not fully configured in environment variables")

    with get_session() as db:
        user = crud.user.get_by_email(db, email=email.lower())
        if user:
            print(f"Superuser '{email}' already exists. Skipping creation.")
            return

        user_in = schemas.UserCreate(
            email=email,
            username=username,
            full_name=settings.FIRST_SUPERUSER_FULL_NAME,
            password=password,
            is_active=True,
            is_superuser=True,
        )
        crud.user.create(db, obj_in=user_in)
        print(f"Superuser '{email}' created successfully.")


def main() -> None:
    init_superuser()


if __name__ == "__main__":
    main()
