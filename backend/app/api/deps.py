from typing import Annotated, TypeAlias

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.core.logger_init import setup_logging
from app.db.session import get_db

logger = setup_logging()
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Annotated type aliases for dependency injection
DbSession: TypeAlias = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession, token: str = Depends(reusable_oauth2)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = schemas.TokenPayload(**payload)
    except (JWTError, ValidationError) as err:
        raise credentials_exception from err

    if token_data.sub is None:
        raise credentials_exception

    try:
        user_id = int(token_data.sub)
    except ValueError as exc:
        raise credentials_exception from exc

    user = crud.user.get(db, id=user_id)
    if user is None:
        raise credentials_exception
    return user


AuthenticatedUser: TypeAlias = Annotated[models.User, Depends(get_current_user)]


def get_current_active_user(current_user: AuthenticatedUser) -> models.User:
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(current_user: AuthenticatedUser) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user


CurrentUser: TypeAlias = Annotated[models.User, Depends(get_current_active_user)]
CurrentSuperuser: TypeAlias = Annotated[models.User, Depends(get_current_active_superuser)]


# Ownership dependencies for each resource type
# Usage: bill: models.Bill = Depends(deps.get_user_bill)
def get_user_bill(
    bill_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> models.Bill:
    """Get a bill owned by the current user"""
    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        logger.warning(f"User {current_user.id} attempted to access non-existent bill {bill_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    if bill.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to bill {bill_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this bill")
    return bill


def get_user_goal(
    goal_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> models.Goal:
    """Get a goal owned by the current user"""
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        logger.warning(f"User {current_user.id} attempted to access non-existent goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    if goal.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this goal")
    return goal


def get_user_transaction(
    transaction_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> models.Transactions:
    """Get a transaction owned by the current user"""
    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        logger.warning(f"User {current_user.id} attempted to access non-existent transaction {transaction_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if transaction.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to transaction {transaction_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this transaction")
    return transaction


def get_user_budget(
    budget_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> models.Budget:
    """Get a budget owned by the current user"""
    budget = crud.budget.get(db, id=budget_id)
    if not budget:
        logger.warning(f"User {current_user.id} attempted to access non-existent budget {budget_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if budget.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to budget {budget_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this budget")
    return budget


def get_user_category(
    category_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> models.Category:
    """Get a category accessible by the current user (own or system category)"""
    category = crud.category.get(db, id=category_id)
    if not category:
        logger.warning(f"User {current_user.id} attempted to access non-existent category {category_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    # Allow system categories (user_id=None) or user's own categories
    if category.user_id is not None and category.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this category")
    return category


# Validation helpers for related resources (used in create/update operations)
# These are NOT FastAPI dependencies - call them directly in endpoint code

def validate_category_access(db: Session, category_id: int, user_id: int) -> models.Category:
    """
    Validate that a category exists and is accessible by the user.
    Used when creating/updating resources that reference a category.
    Allows system categories (user_id=None) or user's own categories.
    """
    category = crud.category.get(db, id=category_id)
    if not category:
        logger.warning(f"User {user_id} attempted to use non-existent category {category_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category.user_id is not None and category.user_id != user_id:
        logger.warning(f"User {user_id} attempted unauthorized use of category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this category")
    return category


def validate_goal_access(db: Session, goal_id: int, user_id: int) -> models.Goal:
    """
    Validate that a goal exists and is owned by the user.
    Used when creating/updating resources that reference a goal.
    """
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        logger.warning(f"User {user_id} attempted to use non-existent goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    if goal.user_id != user_id:
        logger.warning(f"User {user_id} attempted unauthorized use of goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this goal")
    return goal


def get_user_owned_category(
    category_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> models.Category:
    """
    Get a category that is owned by the current user (NOT system categories).
    Use this for update/delete operations where we need to verify the user owns the category.
    """
    category = crud.category.get(db, id=category_id)
    if not category:
        logger.warning(f"User {current_user.id} attempted to access non-existent category {category_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category.user_id is None:
        logger.warning(f"User {current_user.id} attempted to modify system category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system categories")
    if category.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this category")
    return category
