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
    goal: models.Goal = Depends(deps.get_user_goal),
) -> schemas.GoalRead:
    return schemas.GoalRead.model_validate(goal)


@router.get("/{goal_id}/progress", response_model=schemas.GoalWithProgress)
def read_goal_with_progress(
    *,
    db: Session = Depends(deps.get_db),
    goal: models.Goal = Depends(deps.get_user_goal),
) -> schemas.GoalWithProgress:
    logger.info(f"User {goal.user_id} is retrieving progress for goal {goal.id}")

    progress = crud.goal.calculate_progress(db, goal_id=goal.id)
    goal_dict = schemas.GoalRead.model_validate(goal).model_dump()
    goal_dict.update(progress)

    logger.info(
        f"User {goal.user_id} goal {goal.id} progress: "
        f"${progress['current_amount']:.2f}/${goal.target_amount:.2f} ({progress['progress_percentage']:.1f}%)"
    )

    return schemas.GoalWithProgress(**goal_dict)


@router.put("/{goal_id}", response_model=schemas.GoalRead)
def update_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal: models.Goal = Depends(deps.get_user_goal),
    goal_in: schemas.GoalUpdate,
) -> schemas.GoalRead:
    logger.info(f"User {goal.user_id} is updating goal {goal.id}")
    goal = crud.goal.update(db, db_obj=goal, obj_in=goal_in)
    logger.info(f"User {goal.user_id} successfully updated goal {goal.id}")
    return schemas.GoalRead.model_validate(goal)


@router.delete("/{goal_id}", response_model=schemas.GoalRead)
def delete_goal(
    *,
    db: Session = Depends(deps.get_db),
    goal: models.Goal = Depends(deps.get_user_goal),
) -> schemas.GoalRead:
    logger.info(f"User {goal.user_id} is deleting goal {goal.id}")
    deleted_goal = crud.goal.remove(db, id=goal.id)
    logger.info(f"User {goal.user_id} successfully deleted goal {goal.id}")
    return schemas.GoalRead.model_validate(deleted_goal)
