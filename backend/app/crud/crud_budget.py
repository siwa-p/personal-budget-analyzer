from sqlalchemy import and_, extract, func, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transactions
from app.schemas.budget import BudgetCreate, BudgetUpdate


class CRUDBudget(CRUDBase[Budget, BudgetCreate, BudgetUpdate]):
    def __init__(self):
        super().__init__(Budget)

    def get_budgets_for_month(
        self, db: Session,
        *, user_id: int,
        year: int,
        month: int,
        category_id: int | None = None
    ) -> list[Budget]:
        """Get budgets for a specific month, optionally filtered by category"""
        conditions = [
            Budget.user_id == user_id,
            Budget.year == year,
            Budget.month == month
        ]

        if category_id is not None:
            conditions.append(Budget.category_id == category_id)

        stmt = select(Budget).where(and_(*conditions))
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, *, obj_in: BudgetCreate, user_id: int) -> Budget:
        """Create or update a budget for a user"""
        # Check if budget already exists for this user/month/category
        existing = self.get_budgets_for_month(
            db,
            user_id=user_id,
            year=obj_in.year,
            month=obj_in.month,
            category_id=obj_in.category_id
        )

        if existing:
            # Update existing budget
            self.update(db, db_obj=existing[0], obj_in=obj_in)
            return existing[0]

        # Create new budget
        db_obj = Budget(
            user_id=user_id,
            year=obj_in.year,
            month=obj_in.month,
            category_id=obj_in.category_id,
            amount=obj_in.amount
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_spending_for_budget(
        self, db: Session, *, user_id: int, year: int, month: int, category_id: int | None = None
    ) -> float:
        """Calculate actual spending for a given month/category"""
        conditions = [
            Transactions.user_id == user_id,
            Category.type == "expense",
            extract("year", Transactions.transaction_date) == year,
            extract("month", Transactions.transaction_date) == month
        ]

        if category_id is not None:
            conditions.append(Transactions.category_id == category_id)

        stmt = (
            select(func.sum(Transactions.amount))
            .join(Category, Transactions.category_id == Category.id)
            .where(and_(*conditions))
        )

        result = db.execute(stmt).scalar()
        return float(result) if result else 0.0


budget = CRUDBudget()
