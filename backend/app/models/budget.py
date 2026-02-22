from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User

class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint('user_id', 'year', 'month', 'category_id', name='uix_user_year_month_category'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["Category"] = relationship("Category", back_populates="budgets")

    def __repr__(self) -> str:
        return (
            f"<Budget(id={self.id}, user_id={self.user_id}, month={self.month}, "
            f"year={self.year}, category_id={self.category_id}, amount={self.amount})>"
        )
