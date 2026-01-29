from sqlalchemy import Date, DateTime, ForeignKey, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Transactions(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date: Mapped[Date] = mapped_column(Date, nullable=False)
    bill_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bills.id"), nullable=True)
    goal_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("goals.id"), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)  # 'income' or 'expense'
    account_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, date={self.transaction_date})>"
   