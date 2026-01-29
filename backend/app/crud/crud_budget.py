from sqlalchemy.orm import Session
from sqlalchemy import and_, func, select, extract
from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.models.category import Category
from app.models.transaction import Transactions

class CRUDBudget:
    def get(self, db: Session, id: int) -> Budget:
        stmt = select(Budget).where(Budget.id == id)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[Budget]:
        stmt = select(Budget).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

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
            self.update(
                db,
                db_obj=existing[0],
                obj_in=obj_in
            )
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

    def update(self, db: Session, *, db_obj: Budget, obj_in: BudgetUpdate) -> Budget:
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Budget:
        """Delete a budget"""
        obj = db.get(Budget, id)
        db.delete(obj)
        db.commit()
        return obj

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