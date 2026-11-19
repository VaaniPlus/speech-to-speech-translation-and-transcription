"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    bearer_scheme,
    create_access_token,
    get_token_subject,
    hash_password,
    verify_password,
)
from app.db import get_db, get_optional_db
from app.models.user import User
from app.schemas.auth import AuthRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email)


def _resolve_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    db: Session | None,
) -> User:
    if credentials is None or db is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = get_token_subject(credentials, request.app.state.settings.jwt_secret_key)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_authenticated_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session | None, Depends(get_optional_db)],
) -> User | None:
    """Resolve the bearer-token account without requiring auth for public routes."""
    if credentials is None:
        return None
    return _resolve_user(request, credentials, db)


def get_authenticated_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session | None, Depends(get_optional_db)],
) -> User:
    """Require and resolve the bearer-token account."""
    return _resolve_user(request, credentials, db)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: AuthRequest, request: Request, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Create a local account and return an access token."""
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from None
    db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(
            str(user.id),
            request.app.state.settings.jwt_secret_key,
            request.app.state.settings.access_token_expire_minutes,
        ),
        user=_user_response(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: AuthRequest, request: Request, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Authenticate an account and return an access token."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return TokenResponse(
        access_token=create_access_token(
            str(user.id),
            request.app.state.settings.jwt_secret_key,
            request.app.state.settings.access_token_expire_minutes,
        ),
        user=_user_response(user),
    )


@router.get("/me", response_model=UserResponse)
def current_user(
    user: Annotated[User, Depends(get_authenticated_user)],
) -> UserResponse:
    """Return the account represented by the bearer token."""
    return _user_response(user)
