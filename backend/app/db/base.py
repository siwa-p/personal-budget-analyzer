from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

# Import models here so SQLAlchemy registers them with the metadata
from app import models  # noqa: F401,E402
