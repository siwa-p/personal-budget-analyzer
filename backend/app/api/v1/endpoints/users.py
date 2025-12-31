from typing import List
from app.core.logger_init import setup_logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

logger = setup_logging()
router = APIRouter()


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: models.User = Depends(deps.get_current_active_user)) -> schemas.UserRead:
    logger.info(f"User {current_user.id} accessed their profile.")
    return schemas.UserRead.model_validate(current_user)


@router.get("/", response_model=List[schemas.UserRead])
def read_users(
    *, db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100, current_user: models.User = Depends(deps.get_current_active_superuser)
) -> List[schemas.UserRead]:
    logger.info(f"Superuser {current_user.id} is retrieving user list.")
    users = crud.user.get_multi(db, skip=skip, limit=limit)
    return [schemas.UserRead.model_validate(user) for user in users]


@router.post("/", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    *, db: Session = Depends(deps.get_db), user_in: schemas.UserCreate, current_user: models.User = Depends(deps.get_current_active_superuser)
) -> schemas.UserRead:
    logger.info(f"Superuser {current_user.id} is creating a new user.")
    existing_email = crud.user.get_by_email(db, email=user_in.email.lower())
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    existing_username = crud.user.get_by_username(db, username=user_in.username)
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = crud.user.create(db, obj_in=user_in)
    return schemas.UserRead.model_validate(user)

@router.get("/{user_id}", response_model=schemas.UserRead)
def read_user_by_id(
    *, db: Session = Depends(deps.get_db), user_id: int, current_user: models.User = Depends(deps.get_current_active_superuser)
) -> schemas.UserRead:
    logger.info(f"Superuser {current_user.id} is retrieving user {user_id}.")
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return schemas.UserRead.model_validate(user)

@router.put("/{user_id}", response_model=schemas.UserRead)
def update_user(
    *, db: Session = Depends(deps.get_db), user_id: int, user_in: schemas.UserUpdate, current_user: models.User = Depends(deps.get_current_active_superuser)
) -> schemas.UserRead:
    logger.info(f"Superuser {current_user.id} is updating user {user_id}.")
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_in.email:
        existing_email = crud.user.get_by_email(db, email=user_in.email.lower())
        if existing_email and existing_email.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if user_in.username:
        existing_username = crud.user.get_by_username(db, username=user_in.username)
        if existing_username and existing_username.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = crud.user.update(db, db_obj=user, obj_in=user_in)
    return schemas.UserRead.model_validate(user)

@router.delete("/{user_id}", response_model=schemas.UserRead)
def delete_user(
    *, db: Session = Depends(deps.get_db), user_id: int, current_user: models.User = Depends(deps.get_current_active_superuser)
) -> schemas.UserRead:
    logger.info(f"Superuser {current_user.id} is deleting user {user_id}.")
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user = crud.user.remove(db, id=user_id)
    return schemas.UserRead.model_validate(user)