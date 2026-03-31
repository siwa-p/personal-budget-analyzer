
from fastapi import APIRouter, HTTPException, status

from app import crud, schemas
from app.api.deps import CurrentSuperuser, CurrentUser, DbSession
from app.core.logger_init import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: CurrentUser) -> schemas.UserRead:
    logger.info(f"User {current_user.id} accessed their profile")
    return schemas.UserRead.model_validate(current_user)


@router.put("/me", response_model=schemas.UserRead)
def update_users_me(
    *,
    db: DbSession,
    user_in: schemas.UserUpdate,
    current_user: CurrentUser,
) -> schemas.UserRead:
    logger.info(f"User {current_user.id} is updating their profile")
    update_data = user_in.model_dump(exclude_unset=True, exclude={"is_active", "is_superuser"})

    email = update_data.get("email")
    if email:
        existing_email = crud.user.get_by_email(db, email=email.lower())
        if existing_email and existing_email.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    username = update_data.get("username")
    if username:
        existing_username = crud.user.get_by_username(db, username=username)
        if existing_username and existing_username.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = crud.user.update(db, db_obj=current_user, obj_in=update_data)
    logger.info(f"User {current_user.id} successfully updated their profile")
    return schemas.UserRead.model_validate(user)


@router.get("/", response_model=list[schemas.UserRead])
def read_users(
    *,
    db: DbSession,
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentSuperuser,
) -> list[schemas.UserRead]:
    logger.info(f"Superuser {current_user.id} is retrieving user list")
    users = crud.user.get_multi(db, skip=skip, limit=limit)
    return [schemas.UserRead.model_validate(user) for user in users]


@router.post("/", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    *,
    db: DbSession,
    user_in: schemas.UserCreate,
    current_user: CurrentSuperuser,
) -> schemas.UserRead:
    logger.info(
        f"Superuser {current_user.id} is creating a new user - "
        f"username: {user_in.username}, email: {user_in.email}"
    )

    existing_email = crud.user.get_by_email(db, email=user_in.email.lower())
    if existing_email:
        logger.warning(f"Superuser {current_user.id} attempted to create user with duplicate email: {user_in.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    existing_username = crud.user.get_by_username(db, username=user_in.username)
    if existing_username:
        logger.warning(
            f"Superuser {current_user.id} attempted to create user with duplicate username: {user_in.username}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = crud.user.create(db, obj_in=user_in)
    logger.info(f"Superuser {current_user.id} successfully created user {user.id}")
    return schemas.UserRead.model_validate(user)


@router.get("/{user_id}", response_model=schemas.UserRead)
def read_user_by_id(
    *,
    db: DbSession,
    user_id: int,
    current_user: CurrentSuperuser,
) -> schemas.UserRead:
    logger.info(f"Superuser {current_user.id} is retrieving user {user_id}")

    user = crud.user.get(db, id=user_id)
    if not user:
        logger.warning(f"Superuser {current_user.id} attempted to access non-existent user {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return schemas.UserRead.model_validate(user)


@router.put("/{user_id}", response_model=schemas.UserRead)
def update_user(
    *,
    db: DbSession,
    user_id: int,
    user_in: schemas.UserUpdate,
    current_user: CurrentSuperuser,
) -> schemas.UserRead:
    logger.info(f"Superuser {current_user.id} is updating user {user_id}")

    user = crud.user.get(db, id=user_id)
    if not user:
        logger.warning(f"Superuser {current_user.id} attempted to update non-existent user {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_in.email:
        existing_email = crud.user.get_by_email(db, email=user_in.email.lower())
        if existing_email and existing_email.id != user_id:
            logger.warning(
                f"Superuser {current_user.id} attempted to update user {user_id} with duplicate email: {user_in.email}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if user_in.username:
        existing_username = crud.user.get_by_username(db, username=user_in.username)
        if existing_username and existing_username.id != user_id:
            logger.warning(
                f"Superuser {current_user.id} attempted to update user {user_id} with duplicate username: {user_in.username}"
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    user = crud.user.update(db, db_obj=user, obj_in=user_in)
    logger.info(f"Superuser {current_user.id} successfully updated user {user_id}")
    return schemas.UserRead.model_validate(user)


@router.delete("/{user_id}", response_model=schemas.UserRead)
def delete_user(
    *,
    db: DbSession,
    user_id: int,
    current_user: CurrentSuperuser,
) -> schemas.UserRead:
    logger.info(f"Superuser {current_user.id} is deleting user {user_id}")

    user = crud.user.get(db, id=user_id)
    if not user:
        logger.warning(f"Superuser {current_user.id} attempted to delete non-existent user {user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = crud.user.remove(db, id=user_id)
    logger.info(f"Superuser {current_user.id} successfully deleted user {user_id}")
    return schemas.UserRead.model_validate(user)
