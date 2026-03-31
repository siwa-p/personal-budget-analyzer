from pydantic import BaseModel, ConfigDict


class CategoryFeedbackBase(BaseModel):
    description: str
    suggested_category_id: int | None = None
    chosen_category_id: int
    source: str | None = None
    confidence: float | None = None
    transaction_id: int | None = None


class CategoryFeedbackCreate(CategoryFeedbackBase):
    pass


class CategoryFeedbackRead(CategoryFeedbackBase):
    id: int
    user_id: int
    is_correction: bool
    model_config = ConfigDict(from_attributes=True)
