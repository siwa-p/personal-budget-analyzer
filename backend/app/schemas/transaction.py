from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _check_not_future(v: date) -> date:
    if v > date.today():
        raise ValueError('Transaction date cannot be in the future')
    return v


PastOrPresentDate = Annotated[date, AfterValidator(_check_not_future)]


class TransactionBase(BaseModel):
    amount: float
    description: str | None = None
    transaction_date: date
    transaction_type: str = Field(..., pattern="^(income|expense)$")  # 'income' or 'expense'
    account_name: str | None = None


class TransactionCreate(TransactionBase):
    transaction_date: PastOrPresentDate  # validated on write only
    category_id: int
    bill_id: int | None = None
    goal_id: int | None = None


class TransactionUpdate(BaseModel):
    amount: float | None = None
    description: str | None = None
    transaction_date: PastOrPresentDate | None = None
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
