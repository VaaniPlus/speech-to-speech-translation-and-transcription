"""Persistence helpers for per-user conversion history."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.conversion import Conversion, ConversionDirection
from app.models.user import User

MAX_CONVERSIONS_PER_USER = 5


def save_conversion(
    db: Session,
    *,
    user_id: int,
    direction: ConversionDirection,
    source_text: str,
    translated_text: str,
) -> None:
    """Save a completed conversion and remove entries older than the newest five."""
    locked_user_id = db.scalar(
        select(User.id).where(User.id == user_id).with_for_update()
    )
    if locked_user_id is None:
        raise ValueError("Cannot save conversion history for a missing user.")

    conversion = Conversion(
        user_id=user_id,
        direction=direction,
        source_text=source_text,
        translated_text=translated_text,
    )
    db.add(conversion)
    db.flush()

    expired_ids = db.scalars(
        select(Conversion.id)
        .where(Conversion.user_id == user_id)
        .order_by(Conversion.created_at.desc(), Conversion.id.desc())
        .offset(MAX_CONVERSIONS_PER_USER)
    ).all()
    if expired_ids:
        db.execute(delete(Conversion).where(Conversion.id.in_(expired_ids)))
    db.commit()


def get_recent_conversions(db: Session, user_id: int) -> list[Conversion]:
    """Return no more than five conversions for the requested account."""
    return list(
        db.scalars(
            select(Conversion)
            .where(Conversion.user_id == user_id)
            .order_by(Conversion.created_at.desc(), Conversion.id.desc())
            .limit(MAX_CONVERSIONS_PER_USER)
        ).all()
    )
