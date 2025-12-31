from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str
    type: str = Field(..., pattern="^(income|expense)$")  # 'income' or 'expense'


class CategoryCreate(CategoryBase):
    user_id: Optional[int] = None  # None for system categories


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = Field(default=None, pattern="^(income|expense)$")


class CategoryRead(CategoryBase):
    id: int
    user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
