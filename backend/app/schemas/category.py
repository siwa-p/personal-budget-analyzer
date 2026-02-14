
from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str
    type: str = Field(..., pattern="^(income|expense)$")  # 'income' or 'expense'
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    parent_category_id: int | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    type: str | None = Field(default=None, pattern="^(income|expense)$")
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    parent_category_id: int | None = None
    is_active: bool | None = None


class CategoryRead(CategoryBase):
    id: int
    user_id: int | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
