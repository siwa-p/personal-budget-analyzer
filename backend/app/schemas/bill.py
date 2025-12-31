from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BillBase(BaseModel):
    title: str
    amount: Optional[float] = None
    due_date: date
    recurrence: str = "none"
    last_paid_date: Optional[date] = None


class BillCreate(BillBase):
    user_id: int


class BillUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[date] = None
    recurrence: Optional[str] = None
    last_paid_date: Optional[date] = None


class BillRead(BillBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
