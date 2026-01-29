from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.logger_init import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/", response_model=List[schemas.CategoryRead])
def read_categories(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.CategoryRead]:
    logger.info(f"User {current_user.id} is retrieving categories")
    categories = crud.category.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return [schemas.CategoryRead.model_validate(cat) for cat in categories]


@router.get("/system", response_model=List[schemas.CategoryRead])
def read_system_categories(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.CategoryRead]:
    logger.info(f"User {current_user.id} is retrieving system categories")
    categories = crud.category.get_system_categories(db, skip=skip, limit=limit)
    return [schemas.CategoryRead.model_validate(cat) for cat in categories]


@router.post("/", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    *,
    db: Session = Depends(deps.get_db),
    category_in: schemas.CategoryCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.CategoryRead:
    logger.info(f"User {current_user.id} is creating a new category - name: {category_in.name}, type: {category_in.type}")

    # Validate parent category exists and user has access to it
    if category_in.parent_category_id:
        deps.validate_category_access(db, category_in.parent_category_id, current_user.id)

    existing_category = crud.category.get_by_name_and_user(
        db, name=category_in.name, type=category_in.type, user_id=current_user.id
    )
    if existing_category:
        logger.warning(
            f"User {current_user.id} attempted to create duplicate category - "
            f"name: {category_in.name}, type: {category_in.type}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category_in.name}' of type '{category_in.type}' already exists",
        )

    category = crud.category.create(db, obj_in=category_in, user_id=current_user.id)
    logger.info(f"User {current_user.id} successfully created category {category.id}")
    return schemas.CategoryRead.model_validate(category)


@router.get("/{category_id}", response_model=schemas.CategoryRead)
def read_category(
    *,
    category: models.Category = Depends(deps.get_user_category),
) -> schemas.CategoryRead:
    return schemas.CategoryRead.model_validate(category)


@router.put("/{category_id}", response_model=schemas.CategoryRead)
def update_category(
    *,
    db: Session = Depends(deps.get_db),
    category: models.Category = Depends(deps.get_user_owned_category),
    category_in: schemas.CategoryUpdate,
) -> schemas.CategoryRead:
    logger.info(f"User {category.user_id} is updating category {category.id}")

    # Validate parent category if being updated
    if category_in.parent_category_id is not None:
        # Prevent setting itself as parent
        if category_in.parent_category_id == category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )
        deps.validate_category_access(db, category_in.parent_category_id, category.user_id)

    category = crud.category.update(db, db_obj=category, obj_in=category_in)
    logger.info(f"User {category.user_id} successfully updated category {category.id}")
    return schemas.CategoryRead.model_validate(category)


@router.delete("/{category_id}", response_model=schemas.CategoryRead)
def delete_category(
    *,
    db: Session = Depends(deps.get_db),
    category: models.Category = Depends(deps.get_user_owned_category),
    hard_delete: bool = False,
) -> schemas.CategoryRead:
    logger.info(f"User {category.user_id} is deleting category {category.id} (hard_delete={hard_delete})")

    if hard_delete:
        deleted_category = crud.category.remove(db, id=category.id)
        logger.info(f"User {category.user_id} successfully hard deleted category {category.id}")
    else:
        deleted_category = crud.category.soft_delete(db, id=category.id)
        logger.info(f"User {category.user_id} successfully soft deleted (deactivated) category {category.id}")

    return schemas.CategoryRead.model_validate(deleted_category)
