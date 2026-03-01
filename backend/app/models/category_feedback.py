from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class CategoryFeedback(Base):
    __tablename__ = "category_feedback"

    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("transactions.id"), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    suggested_category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    chosen_category_id: Mapped[int] = mapped_column(Integer,ForeignKey("categories.id"), nullable=False)
    is_correction: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<CategoryFeedback(id={self.id}, user_id={self.user_id}, transaction_id={self.transaction_id}, " \
               f"description={self.description}, suggested_category_id={self.suggested_category_id}, " \
               f"chosen_category_id={self.chosen_category_id}, is_correction={self.is_correction}, " \
               f"source={self.source}, confidence={self.confidence})>"
