from sqlalchemy import Date, DateTime, ForeignKey, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    due_date: Mapped[Date] = mapped_column(Date, nullable=False)
    recurrence: Mapped[str] = mapped_column(String, nullable=False, default="none")
    last_paid_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Bill(id={self.id}, user_id={self.user_id}, title={self.title}, "
            f"amount={self.amount}, due_date={self.due_date}, recurrence={self.recurrence})>"
        )
