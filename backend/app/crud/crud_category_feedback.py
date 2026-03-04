from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.category_feedback import CategoryFeedback
from app.schemas.category_feedback import CategoryFeedbackCreate, CategoryFeedbackRead


class CrudCategoryFeedback(CRUDBase[CategoryFeedback, CategoryFeedbackCreate, CategoryFeedbackRead]):
    def __init__(self):
        super().__init__(CategoryFeedback)

    def create(self, db: Session, *, obj_in: CategoryFeedbackCreate, user_id: int) -> CategoryFeedback:
        is_correction = (
            obj_in.suggested_category_id is not None
            and obj_in.suggested_category_id != obj_in.chosen_category_id
        )
        db_obj = CategoryFeedback(
            user_id=user_id,
            transaction_id=obj_in.transaction_id,
            description=obj_in.description,
            suggested_category_id=obj_in.suggested_category_id,
            chosen_category_id=obj_in.chosen_category_id,
            is_correction=is_correction,
            source=obj_in.source,
            confidence=obj_in.confidence,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


category_feedback = CrudCategoryFeedback()
