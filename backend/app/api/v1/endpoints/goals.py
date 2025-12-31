from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.logger_init import setup_logging

logger = setup_logging()
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
    logger.info(f"User {current_user.id} is retrieving goals with status filter: {status_filter}")

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
    logger.info(
        f"User {current_user.id} is creating a new goal - "
        f"name: {goal_in.name}, target: ${goal_in.target_amount}, status: {goal_in.status}"
    )

    goal = crud.goal.create(db, obj_in=goal_in, user_id=current_user.id)
    logger.info(f"User {current_user.id} successfully created goal {goal.id}")
    return schemas.GoalRead.model_validate(goal)


@router.get("/{goal_id}", response_model=schemas.GoalRead)
def read_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalRead:
    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        logger.warning(f"User {current_user.id} attempted to access non-existent goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    if goal.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this goal")

    return schemas.GoalRead.model_validate(goal)


@router.get("/{goal_id}/progress", response_model=schemas.GoalWithProgress)
def read_goal_with_progress(
    *,
    db: Session = Depends(deps.get_db),
    goal_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalWithProgress:
    logger.info(f"User {current_user.id} is retrieving progress for goal {goal_id}")

    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        logger.warning(f"User {current_user.id} attempted to access non-existent goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    if goal.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized access to goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this goal")

    progress = crud.goal.calculate_progress(db, goal_id=goal_id)
    goal_dict = schemas.GoalRead.model_validate(goal).model_dump()
    goal_dict.update(progress)

    logger.info(
        f"User {current_user.id} goal {goal_id} progress: "
        f"${progress['current_amount']:.2f}/${goal.target_amount:.2f} ({progress['progress_percentage']:.1f}%)"
    )

    return schemas.GoalWithProgress(**goal_dict)


@router.put("/{goal_id}", response_model=schemas.GoalRead)
def update_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal_id: int,
    goal_in: schemas.GoalUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalRead:
    logger.info(f"User {current_user.id} is updating goal {goal_id}")

    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        logger.warning(f"User {current_user.id} attempted to update non-existent goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    if goal.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized update of goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this goal")

    goal = crud.goal.update(db, db_obj=goal, obj_in=goal_in)
    logger.info(f"User {current_user.id} successfully updated goal {goal_id}")
    return schemas.GoalRead.model_validate(goal)


@router.delete("/{goal_id}", response_model=schemas.GoalRead)
def delete_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.GoalRead:
    logger.info(f"User {current_user.id} is deleting goal {goal_id}")

    goal = crud.goal.get(db, id=goal_id)
    if not goal:
        logger.warning(f"User {current_user.id} attempted to delete non-existent goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    if goal.user_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted unauthorized deletion of goal {goal_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this goal")

    goal = crud.goal.remove(db, id=goal_id)
    logger.info(f"User {current_user.id} successfully deleted goal {goal_id}")
    return schemas.GoalRead.model_validate(goal)
