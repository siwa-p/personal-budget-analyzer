from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.CategoryRead])
def read_categories(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.CategoryRead]:
    """Get all categories (system + user's own categories)"""
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
    """Get only system categories"""
    categories = crud.category.get_system_categories(db, skip=skip, limit=limit)
    return [schemas.CategoryRead.model_validate(cat) for cat in categories]


@router.post("/", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    *,
    db: Session = Depends(deps.get_db),
    category_in: schemas.CategoryCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.CategoryRead:
    """Create a new category for the current user"""
    # Force user_id to current user (ignore what client sends)
    category_in.user_id = current_user.id
    category = crud.category.create(db, obj_in=category_in)
    return schemas.CategoryRead.model_validate(category)


@router.get("/{category_id}", response_model=schemas.CategoryRead)
def read_category(
    *,
    db: Session = Depends(deps.get_db),
    category_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.CategoryRead:
    """Get category by ID"""
    category = crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Check if user has access (own category or system category)
    if category.user_id and category.user_id != current_user.id:
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
    """Update a category (only user's own categories)"""
    category = crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Don't allow updating system categories
    if category.user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update system categories")

    # Only allow updating own categories
    if category.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this category")

    category = crud.category.update(db, db_obj=category, obj_in=category_in)
    return schemas.CategoryRead.model_validate(category)


@router.delete("/{category_id}", response_model=schemas.CategoryRead)
def delete_category(
    *,
    db: Session = Depends(deps.get_db),
    category_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.CategoryRead:
    """Delete a category (only user's own categories)"""
    category = crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Don't allow deleting system categories
    if category.user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system categories")

    # Only allow deleting own categories
    if category.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this category")

    category = crud.category.remove(db, id=category_id)
    return schemas.CategoryRead.model_validate(category)
