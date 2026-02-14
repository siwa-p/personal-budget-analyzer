from datetime import date

from pydantic import BaseModel, ConfigDict


class BillBase(BaseModel):
    title: str
    amount: float | None = None
    due_date: date
    recurrence: str = "none"
    last_paid_date: date | None = None


class BillCreate(BillBase):
    pass


class BillUpdate(BaseModel):
    title: str | None = None
    amount: float | None = None
    due_date: date | None = None
    recurrence: str | None = None
    last_paid_date: date | None = None


class BillRead(BillBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
