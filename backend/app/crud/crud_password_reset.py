from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


class CRUDPasswordReset:
    def create_token(
        self,
        db: Session,
        *,
        user_id: int,
        token_hash: str,
        expires_in_minutes: int,
    ) -> PasswordResetToken:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        db_obj = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_valid_token(self, db: Session, *, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .where(PasswordResetToken.used_at.is_(None))
            .where(PasswordResetToken.expires_at > now)
        )
        return db.execute(stmt).scalar_one_or_none()

    def mark_used(self, db: Session, *, db_obj: PasswordResetToken) -> PasswordResetToken:
        db_obj.used_at = datetime.now(timezone.utc)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def invalidate_user_tokens(self, db: Session, *, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id)
            .where(PasswordResetToken.used_at.is_(None))
        )
        tokens = list(db.execute(stmt).scalars().all())
        for token in tokens:
            token.used_at = now
        if tokens:
            db.add_all(tokens)
            db.commit()
        return len(tokens)


password_reset = CRUDPasswordReset()
