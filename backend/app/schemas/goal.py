from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GoalBase(BaseModel):
    name: str
    target_amount: float = Field(..., gt=0)
    deadline: Optional[date] = None
    status: str = Field(default="active", pattern="^(active|completed|cancelled)$")


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = Field(default=None, gt=0)
    deadline: Optional[date] = None
    status: Optional[str] = Field(default=None, pattern="^(active|completed|cancelled)$")


class GoalRead(GoalBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class GoalWithProgress(GoalRead):
    """Goal with calculated progress information"""
    current_amount: float = 0.0
    progress_percentage: float = 0.0
    remaining_amount: float = 0.0
