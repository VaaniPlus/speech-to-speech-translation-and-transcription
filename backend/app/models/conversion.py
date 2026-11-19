"""Persisted translation history model."""

from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

ConversionDirection = Literal["en-to-hi", "hi-to-en"]


class Conversion(Base):
    """A completed text or speech translation for one account."""

    __tablename__ = "conversions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    direction: Mapped[ConversionDirection] = mapped_column(String(10))
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
