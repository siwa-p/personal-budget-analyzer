from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str
    type: str = Field(..., pattern="^(income|expense)$")  # 'income' or 'expense'
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_category_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = Field(default=None, pattern="^(income|expense)$")
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_category_id: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryRead(CategoryBase):
    id: int
    user_id: Optional[int] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
