"""Typed request and response schemas for translation workflows."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

TranslationDirection = Literal["en-to-hi", "hi-to-en"]
LanguageCode = Literal["en", "hi"]

LANGUAGES_BY_DIRECTION: dict[TranslationDirection, tuple[LanguageCode, LanguageCode]] = {
    "en-to-hi": ("en", "hi"),
    "hi-to-en": ("hi", "en"),
}
ProcessingStatus = Literal["success"]
ErrorStage = Literal["validation", "stt", "translation", "tts", "unknown"]

NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class TranslationRequest(BaseModel):
    """Text and direction submitted for a translation."""

    model_config = ConfigDict(extra="forbid")

    direction: TranslationDirection = Field(
        description="Translation direction: English to Hindi or Hindi to English."
    )
    source_text: NonEmptyText = Field(
        description="Non-empty source text to translate; surrounding whitespace is removed."
    )


class TranslationResponse(BaseModel):
    """Completed translation and language metadata."""

    model_config = ConfigDict(extra="forbid")

    direction: TranslationDirection = Field(
        description="Translation direction used for this result."
    )
    source_text: NonEmptyText = Field(description="Source text that was translated.")
    source_language: LanguageCode = Field(
        description="Language code of the source text."
    )
    target_language: LanguageCode = Field(
        description="Language code of the translated text."
    )
    detected_language: LanguageCode | None = Field(
        default=None,
        description="Language detected from audio, when available; omitted for typed text.",
    )
    translated_text: NonEmptyText = Field(
        description="Non-empty translated text in the target language."
    )
    status: ProcessingStatus = Field(
        default="success",
        description="Indicates that translation completed successfully.",
    )

    @model_validator(mode="after")
    def validate_languages_match_direction(self) -> "TranslationResponse":
        """Ensure language metadata agrees with the selected direction."""
        expected_languages = LANGUAGES_BY_DIRECTION[self.direction]
        if (self.source_language, self.target_language) != expected_languages:
            raise ValueError("source and target languages must match direction")
        if (
            self.detected_language is not None
            and self.detected_language != self.source_language
        ):
            raise ValueError("detected language must match source language")
        return self


class ErrorResponse(BaseModel):
    """Stable, client-safe error payload for API failures."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["error"] = Field(
        default="error",
        description="Indicates that request processing failed.",
    )
    code: NonEmptyText = Field(
        description="Stable machine-readable error code."
    )
    message: NonEmptyText = Field(
        description="Human-readable error message safe to show to the client."
    )
    stage: ErrorStage | None = Field(
        default=None,
        description="Pipeline stage that failed, when applicable.",
    )
    request_id: str = Field(
        description="Correlation ID for this request, also returned in X-Request-ID.",
    )


__all__ = [
    "ErrorResponse",
    "ErrorStage",
    "LANGUAGES_BY_DIRECTION",
    "LanguageCode",
    "ProcessingStatus",
    "TranslationDirection",
    "TranslationRequest",
    "TranslationResponse",
]
