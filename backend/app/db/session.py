from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logger_init import setup_logging

logger = setup_logging()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    logger.info("Database session created.")
    try:
        yield db
    finally:
        db.close()
        logger.info("Database session closed.")
