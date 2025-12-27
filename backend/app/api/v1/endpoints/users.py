from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: models.User = Depends(deps.get_current_active_user)) -> schemas.UserRead:
    return schemas.UserRead.model_validate(current_user)


@router.get("/", response_model=List[schemas.UserRead])
def read_users(
    *, db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100, current_user: models.User = Depends(deps.get_current_active_superuser)
) -> List[schemas.UserRead]:
    users = crud.user.get_multi(db, skip=skip, limit=limit)
    return [schemas.UserRead.model_validate(user) for user in users]


@router.post("/", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    *, db: Session = Depends(deps.get_db), user_in: schemas.UserCreate, current_user: models.User = Depends(deps.get_current_active_superuser)
) -> schemas.UserRead:
    existing_email = crud.user.get_by_email(db, email=user_in.email.lower())
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    existing_username = crud.user.get_by_username(db, username=user_in.username)
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = crud.user.create(db, obj_in=user_in)
    return schemas.UserRead.model_validate(user)
