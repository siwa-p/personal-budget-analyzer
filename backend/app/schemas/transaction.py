from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    amount: float
    description: str | None = None
    transaction_date: date
    transaction_type: str = Field(..., pattern="^(income|expense)$")  # 'income' or 'expense'
    account_name: str | None = None


class TransactionCreate(TransactionBase):
    category_id: int
    bill_id: int | None = None
    goal_id: int | None = None


class TransactionUpdate(BaseModel):
    amount: float | None = None
    description: str | None = None
    transaction_date: date | None = None
    transaction_type: str | None = Field(default=None, pattern="^(income|expense)$")
    account_name: str | None = None
    category_id: int | None = None
    bill_id: int | None = None
    goal_id: int | None = None


class TransactionRead(TransactionBase):
    id: int
    user_id: int
    category_id: int
    bill_id: int | None = None
    goal_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
