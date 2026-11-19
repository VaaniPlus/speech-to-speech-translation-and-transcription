"""Database session and table setup helpers."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.security import hash_password


class Base(DeclarativeBase):
    """Base class for application database models."""


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped database session and initialize local tables."""
    engine = getattr(request.app.state, "database_engine", None)
    if engine is None:
        engine = create_engine(request.app.state.settings.database_url)
        from app.models.user import User  # noqa: F401

        Base.metadata.create_all(engine)
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

    with Session(engine) as session:
        yield session
