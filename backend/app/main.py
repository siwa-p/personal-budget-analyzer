from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logger_init import setup_logging
from app.db.base import Base
from app.db.init_db import init_db
from app.db.session import engine, get_session

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    with get_session() as db:
        init_db(db)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured.")

@app.get("/")
async def root():
    logger.info("Root endpoint accessed.")
    return {
        "message": "Welcome to Personal Budget Analyzer API",
        "version": settings.VERSION,
        "docs": "/docs"
    }

app.include_router(api_router, prefix=settings.API_V1_STR)
