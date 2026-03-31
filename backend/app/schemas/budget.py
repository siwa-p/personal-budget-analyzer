from datetime import datetime

from pydantic import BaseModel, Field


class BudgetBase(BaseModel):
    year: int = Field(..., ge=2000, le=2100, description="Year of the budget")
    month: int = Field(..., ge=1, le=12, description="Month of the budget")
    category_id: int | None = Field(None, description="ID of the category")
    amount: float = Field(..., gt=0, description="Budgeted amount")

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount: float | None = Field(None, gt=0, description="Updated budgeted amount")

class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BudgetWithCategory(BudgetResponse):
    spent: float = Field(..., description="Amount spent in this budget category")
    remaining: float = Field(..., description="Remaining budget amount")
    percentage_used: float = Field(..., description="Percentage of budget used")
    category_name: str | None = Field(None, description="Name of the category")

