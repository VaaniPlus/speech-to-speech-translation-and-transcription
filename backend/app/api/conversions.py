"""Conversion history API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_authenticated_user
from app.db import get_optional_db
from app.models.user import User
from app.schemas.conversion import ConversionResponse
from app.services.conversion_history import get_recent_conversions

router = APIRouter(prefix="/conversions", tags=["conversions"])


@router.get("/history", response_model=list[ConversionResponse])
def conversion_history(
    user: Annotated[User, Depends(get_authenticated_user)],
    db: Annotated[Session | None, Depends(get_optional_db)],
) -> list[ConversionResponse]:
    """Return the signed-in user's five most recent conversions."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return [
        ConversionResponse.model_validate(conversion)
        for conversion in get_recent_conversions(db, user.id)
    ]
