import json
import secrets
import time
import urllib.request
from typing import Annotated, TypeAlias

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models
from app.core.config import settings
from app.core.logger_init import setup_logging
from app.db.session import get_db

logger = setup_logging()
reusable_oauth2 = HTTPBearer()

DbSession: TypeAlias = Annotated[Session, Depends(get_db)]

_jwks_cache: dict = {}
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600


def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.time()
    if _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache
    with urllib.request.urlopen(settings.COGNITO_JWKS_URL) as resp:
        _jwks_cache = json.loads(resp.read())
    _jwks_fetched_at = now
    return _jwks_cache


def get_current_user(db: DbSession, credentials: HTTPAuthorizationCredentials = Depends(reusable_oauth2)) -> models.User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            _get_jwks(),
            algorithms=["RS256"],
            audience=settings.COGNITO_APP_CLIENT_ID,
            issuer=f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}",
        )
    except JWTError:
        raise credentials_exception

    cognito_sub = payload.get("sub")
    if not cognito_sub:
        raise credentials_exception

    if not payload.get("email_verified", False):
        raise credentials_exception

    user = db.execute(select(models.User).where(models.User.cognito_sub == cognito_sub)).scalar_one_or_none()
    if user is None:
        from app.core.security import get_password_hash
        email = payload.get("email", "")
        base_username = email.split("@")[0]
        username = f"{base_username}_{secrets.token_hex(4)}"
        while db.execute(select(models.User).where(models.User.username == username)).scalar_one_or_none():
            username = f"{base_username}_{secrets.token_hex(4)}"
        user = models.User(
            email=email,
            username=username,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            cognito_sub=cognito_sub,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Auto-provisioned user {email}")

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


def get_user_bill(bill_id: int, db: DbSession, current_user: CurrentUser) -> models.Bill:
    bill = crud.bill.get(db, id=bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    if bill.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this bill")
    return bill


def get_user_goal(goal_id: int, db: DbSession, current_user: CurrentUser) -> models.Goal:
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    if goal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this goal")
    return goal


def get_user_transaction(transaction_id: int, db: DbSession, current_user: CurrentUser) -> models.Transactions:
    transaction = crud.transaction.get(db, id=transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this transaction")
    return transaction


def get_user_budget(budget_id: int, db: DbSession, current_user: CurrentUser) -> models.Budget:
    budget = crud.budget.get(db, id=budget_id)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if budget.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this budget")
    return budget


def get_user_category(category_id: int, db: DbSession, current_user: CurrentUser) -> models.Category:
    category = crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category.user_id is not None and category.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this category")
    return category


def validate_category_access(db: Session, category_id: int, user_id: int) -> models.Category:
    category = crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category.user_id is not None and category.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this category")
    return category


def validate_goal_access(db: Session, goal_id: int, user_id: int) -> models.Goal:
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    if goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this goal")
    return goal


def get_user_owned_category(category_id: int, db: DbSession, current_user: CurrentUser) -> models.Category:
    category = crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category.user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system categories")
    if category.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this category")
    return category


UserTransaction: TypeAlias = Annotated[models.Transactions, Depends(get_user_transaction)]
UserBill: TypeAlias = Annotated[models.Bill, Depends(get_user_bill)]
UserGoal: TypeAlias = Annotated[models.Goal, Depends(get_user_goal)]
UserBudget: TypeAlias = Annotated[models.Budget, Depends(get_user_budget)]
UserCategory: TypeAlias = Annotated[models.Category, Depends(get_user_category)]
UserOwnedCategory: TypeAlias = Annotated[models.Category, Depends(get_user_owned_category)]
