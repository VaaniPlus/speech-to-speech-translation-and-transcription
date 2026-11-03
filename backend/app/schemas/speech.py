"""Typed speech-processing response schemas."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.translation import LanguageCode

NonEmptyTranscript = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class SpeechToTextResponse(BaseModel):
    """Successful transcription with requested and detected language metadata."""

    model_config = ConfigDict(extra="forbid")

    transcript: NonEmptyTranscript = Field(
        description="Recognized non-empty speech transcript."
    )
    requested_language: LanguageCode | None = Field(
        description="Requested English/Hindi language, or null for automatic detection."
    )
    detected_language: LanguageCode = Field(
        description="Detected or provider-reported transcript language."
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Provider confidence when available, between zero and one.",
    )
    status: Literal["success"] = "success"
