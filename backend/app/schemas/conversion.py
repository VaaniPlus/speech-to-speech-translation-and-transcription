"""Conversion history response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ConversionResponse(BaseModel):
    """A user's previous translation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    direction: Literal["en-to-hi", "hi-to-en"]
    source_text: str
    translated_text: str
    created_at: datetime
