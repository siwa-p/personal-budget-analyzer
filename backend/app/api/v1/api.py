from fastapi import APIRouter
from app.core.config import settings

from app.api.v1.endpoints import analytics, bills, budgets, categories, goals, transactions, users

api_router = APIRouter()

@api_router.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(bills.router, prefix="/bills", tags=["bills"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
