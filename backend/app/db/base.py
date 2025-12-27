from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey

class Base(DeclarativeBase):
    pass

class Transactions(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer,ForeignKey("categories.id") ,nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date: Mapped[Date] = mapped_column(Date, nullable=False)
    bill_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bills.id"), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)  # 'income' or 'expense'
    account_name: Mapped[str | None] = mapped_column(String, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, date={self.transaction_date})>"
    

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=False, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.00)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email}, balance={self.balance})>"
    
class Bills(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=True)
    due_date: Mapped[Date] = mapped_column(Date, nullable=False)
    recurrence: Mapped[str] = mapped_column(String, nullable=False, default="none")
    last_paid_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return f"<Bill(id={self.id}, user_id={self.user_id}, title={self.title}, amount={self.amount}, due_date={self.due_date}, recurrence={self.recurrence})>"
    
class Categories(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=False, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # 'income' or 'expense'
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, type={self.type}, user_id={self.user_id})>"


class Goals(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    deadline: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # 'active', 'completed', 'cancelled'

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, user_id={self.user_id}, name={self.name}, target_amount={self.target_amount}, status={self.status})>"
    
class GoalTransactions(Base):
    __tablename__ = "goal_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal_id: Mapped[int] = mapped_column(Integer, ForeignKey("goals.id"), nullable=False)
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id"), nullable=False)

    def __repr__(self) -> str:
        return f"<GoalTransaction(id={self.id}, goal_id={self.goal_id}, transaction_id={self.transaction_id})>"
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import models here so SQLAlchemy registers them with the metadata
from app import models  # noqa: F401,E402
