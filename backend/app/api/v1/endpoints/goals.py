from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.GoalRead])
def read_goals(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = Query(default=None, pattern="^(active|completed|cancelled)$", alias="status"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[schemas.GoalRead]:
    """Get all goals for the current user, optionally filtered by status"""
    if status_filter:
        goals = crud.goal.get_by_status(
            db, user_id=current_user.id, status=status_filter, skip=skip, limit=limit
        )
    else:
        goals = crud.goal.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)

    return [schemas.GoalRead.model_validate(goal) for goal in goals]


@router.post("/", response_model=schemas.GoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal_in: schemas.GoalCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalRead:
    """Create a new goal"""
    # Force user_id to current user
    goal_in.user_id = current_user.id
    goal = crud.goal.create(db, obj_in=goal_in)
    return schemas.GoalRead.model_validate(goal)


@router.get("/{goal_id}", response_model=schemas.GoalRead)
def read_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalRead:
    """Get goal by ID"""
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    # Only allow access to own goals
    if goal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this goal")

    return schemas.GoalRead.model_validate(goal)


@router.put("/{goal_id}", response_model=schemas.GoalRead)
def update_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal_id: int,
    goal_in: schemas.GoalUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalRead:
    """Update a goal"""
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    # Only allow updating own goals
    if goal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this goal")

    goal = crud.goal.update(db, db_obj=goal, obj_in=goal_in)
    return schemas.GoalRead.model_validate(goal)


@router.delete("/{goal_id}", response_model=schemas.GoalRead)
def delete_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalRead:
    """Delete a goal"""
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    # Only allow deleting own goals
    if goal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this goal")

    goal = crud.goal.remove(db, id=goal_id)
    return schemas.GoalRead.model_validate(goal)
