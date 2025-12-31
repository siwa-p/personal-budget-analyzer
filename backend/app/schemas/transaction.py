from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    amount: float
    description: Optional[str] = None
    transaction_date: date
    transaction_type: str = Field(..., pattern="^(income|expense)$")  # 'income' or 'expense'
    account_name: Optional[str] = None


class TransactionCreate(TransactionBase):
    category_id: int
    bill_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    transaction_date: Optional[date] = None
    transaction_type: Optional[str] = Field(default=None, pattern="^(income|expense)$")
    account_name: Optional[str] = None
    category_id: Optional[int] = None
    bill_id: Optional[int] = None


class TransactionRead(TransactionBase):
    id: int
    user_id: int
    category_id: int
    bill_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
