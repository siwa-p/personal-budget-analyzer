from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import engine, get_db
from app.db.base import Base, Users, Categories

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Personal Budget Analyzer API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


# API v1 routes would be added here
# from app.api.v1.api import api_router
# app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/test/users")
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(Users).all()
    return {
        "count": len(users),
        "users": [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "balance": user.balance
            }
            for user in users
        ]
    }

@app.get("/test/categories")
async def get_all_categories(db: Session = Depends(get_db)):
    categories = db.query(Categories).all()
    return {
        "count": len(categories),
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "type": cat.type,
                "user_id": cat.user_id
            }
            for cat in categories
        ]
    }
