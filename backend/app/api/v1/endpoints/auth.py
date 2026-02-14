import hashlib
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app import crud, schemas
from app.api.deps import DbSession
from app.core import security
from app.core.config import settings
from app.core.logger_init import setup_logging
from app.tasks.email import send_password_reset_email

logger = setup_logging()
router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: DbSession, form_data: OAuth2PasswordRequestForm = Depends()
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
def register_user(*, db: DbSession, user_in: schemas.UserCreate) -> schemas.UserRead:
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


@router.post("/forgot-password", response_model=schemas.Message)
def forgot_password(*, db: DbSession, payload: schemas.PasswordResetRequest) -> schemas.Message:
    logger.info(f"Password reset requested for {payload.email}.")
    user = crud.user.get_by_email(db, email=payload.email.lower())
    if user and crud.user.is_active(user):
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        crud.password_reset.invalidate_user_tokens(db, user_id=user.id)
        crud.password_reset.create_token(
            db,
            user_id=user.id,
            token_hash=token_hash,
            expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD or not settings.MAIL_FROM:
            logger.error("Email settings are not configured for password reset.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Email not configured")
        reset_url = (
            f"{settings.FRONTEND_URL.rstrip('/')}{settings.PASSWORD_RESET_PATH}?token={token}"
        )
        send_password_reset_email.delay(payload.email, reset_url)
    return schemas.Message(message="If the email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=schemas.Message)
def reset_password(*, db: DbSession, payload: schemas.PasswordResetConfirm) -> schemas.Message:
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    db_token = crud.password_reset.get_valid_token(db, token_hash=token_hash)
    if not db_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    user = crud.user.get(db, id=db_token.user_id)
    if not user or not crud.user.is_active(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or inactive user")
    crud.password_reset.mark_used(db, db_obj=db_token)
    crud.user.update(db, db_obj=user, obj_in={"password": payload.new_password})
    return schemas.Message(message="Password updated successfully.")
