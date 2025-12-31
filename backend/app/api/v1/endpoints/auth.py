from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.logger_init import setup_logging
logger = setup_logging()
router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> schemas.Token:
    logger.info(f"User {form_data.username} is attempting to log in.")
    user = crud.user.authenticate(db, email=form_data.username, password=form_data.password)
    if not user:
        logger.info(f"Authentication failed for user {form_data.username}.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    if not crud.user.is_active(user):
        logger.info(f"Inactive user {form_data.username} attempted to log in.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return schemas.Token(
        access_token=security.create_access_token(subject=user.id, expires_delta=access_token_expires),
        token_type="bearer",
    )


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register_user(*, db: Session = Depends(deps.get_db), user_in: schemas.UserCreate) -> schemas.UserRead:
    logger.info(f"Registering new user with email {user_in.email}.")
    existing_email = crud.user.get_by_email(db, email=user_in.email.lower())
    if existing_email:
        logger.info(f"Registration failed: Email {user_in.email} already registered.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    existing_username = crud.user.get_by_username(db, username=user_in.username)
    if existing_username:
        logger.info(f"Registration failed: Username {user_in.username} already taken.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    sanitized_user = user_in.model_copy(update={"is_superuser": False, "is_active": True})
    user = crud.user.create(db, obj_in=sanitized_user)
    return schemas.UserRead.model_validate(user)
