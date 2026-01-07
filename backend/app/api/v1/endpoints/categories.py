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
        parent_category = crud.category.get(db, id=category_in.parent_category_id)
        if not parent_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found"
            )
        # Check if parent is accessible (system category or user's own category)
        if parent_category.user_id and parent_category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to use this parent category"
            )

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
    db: Session = Depends(deps.get_db),
    category_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.CategoryRead:
    category = crud.category.get(db, id=category_id)
    if not category:
        logger.warning(f"User {current_user.id} attempted to access non-existent category {category_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category.user_id and category.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this category")

    return schemas.CategoryRead.model_validate(category)


@router.put("/{category_id}", response_model=schemas.CategoryRead)
def update_category(
    *,
    db: Session = Depends(deps.get_db),
    category_id: int,
    category_in: schemas.CategoryUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.CategoryRead:
    logger.info(f"User {current_user.id} is updating category {category_id}")

    category = crud.category.get(db, id=category_id)
    if not category:
        logger.warning(f"User {current_user.id} attempted to update non-existent category {category_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category.user_id is None:
        logger.warning(f"User {current_user.id} attempted to update system category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update system categories")

    if category.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized update of category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this category")

    # Validate parent category if being updated
    if category_in.parent_category_id is not None:
        # Prevent setting itself as parent
        if category_in.parent_category_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )

        parent_category = crud.category.get(db, id=category_in.parent_category_id)
        if not parent_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found"
            )
        # Check if parent is accessible (system category or user's own category)
        if parent_category.user_id and parent_category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to use this parent category"
            )

    category = crud.category.update(db, db_obj=category, obj_in=category_in)
    logger.info(f"User {current_user.id} successfully updated category {category_id}")
    return schemas.CategoryRead.model_validate(category)


@router.delete("/{category_id}", response_model=schemas.CategoryRead)
def delete_category(
    *,
    db: Session = Depends(deps.get_db),
    category_id: int,
    hard_delete: bool = False,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.CategoryRead:
    logger.info(f"User {current_user.id} is deleting category {category_id} (hard_delete={hard_delete})")

    category = crud.category.get(db, id=category_id)
    if not category:
        logger.warning(f"User {current_user.id} attempted to delete non-existent category {category_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if category.user_id is None:
        logger.warning(f"User {current_user.id} attempted to delete system category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system categories")

    if category.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized deletion of category {category_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this category")

    if hard_delete:
        category = crud.category.remove(db, id=category_id)
        logger.info(f"User {current_user.id} successfully hard deleted category {category_id}")
    else:
        category = crud.category.soft_delete(db, id=category_id)
        logger.info(f"User {current_user.id} successfully soft deleted (deactivated) category {category_id}")

    return schemas.CategoryRead.model_validate(category)
