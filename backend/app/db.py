"""Database session and table setup helpers."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.security import bearer_scheme, hash_password


class Base(DeclarativeBase):
    """Base class for application database models."""


def get_database_engine(request: Request) -> Engine:
    """Return the application engine, creating its tables on first use."""
    engine = getattr(request.app.state, "database_engine", None)
    if engine is None:
        engine = create_engine(request.app.state.settings.database_url)
        from app.models.conversion import Conversion
        from app.models.user import User

        Base.metadata.create_all(
            engine,
            tables=[model.__table__ for model in (User, Conversion)],
        )
        settings = request.app.state.settings
        if settings.seed_default_user:
            with Session(engine) as initial_session:
                seeded_user = initial_session.scalar(
                    select(User).where(User.email == settings.default_user_email)
                )
                if seeded_user is None:
                    initial_session.add(
                        User(
                            email=settings.default_user_email,
                            password_hash=hash_password(settings.default_user_password),
                        )
                    )
                    try:
                        initial_session.commit()
                    except IntegrityError:
                        initial_session.rollback()
                        seeded_user = initial_session.scalar(
                            select(User).where(User.email == settings.default_user_email)
                        )
                        if seeded_user is None:
                            raise
        request.app.state.database_engine = engine
    return engine


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped database session and initialize local tables."""
    engine = get_database_engine(request)

    with Session(engine) as session:
        yield session


def get_optional_db(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> Generator[Session | None, None, None]:
    """Open a database session only when the request includes a bearer token."""
    if credentials is None:
        yield None
        return

    with Session(get_database_engine(request)) as session:
        yield session
