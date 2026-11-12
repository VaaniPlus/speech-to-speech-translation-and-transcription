"""Tests for translation request, response, and error schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas import ErrorResponse, TranslationRequest, TranslationResponse


@pytest.mark.parametrize(
    ("direction", "source_text"),
    [
        ("en-to-hi", "Hello"),
        ("hi-to-en", "नमस्ते"),
    ],
)
def test_translation_request_accepts_supported_directions(
    direction: str, source_text: str
) -> None:
    request = TranslationRequest(direction=direction, source_text=source_text)

    assert request.direction == direction
    assert request.source_text == source_text


@pytest.mark.parametrize("source_text", ["", " ", "\t\n"])
def test_translation_request_rejects_empty_or_whitespace_text(
    source_text: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        TranslationRequest(direction="en-to-hi", source_text=source_text)

    assert error.value.errors()[0]["loc"] == ("source_text",)


def test_translation_request_rejects_unsupported_direction() -> None:
    with pytest.raises(ValidationError) as error:
        TranslationRequest(direction="en-to-fr", source_text="Hello")

    assert error.value.errors()[0]["loc"] == ("direction",)


def test_translation_request_strips_surrounding_whitespace() -> None:
    request = TranslationRequest(direction="en-to-hi", source_text="  Hello  ")

    assert request.source_text == "Hello"


@pytest.mark.parametrize(
    ("direction", "source_language", "target_language", "detected_language"),
    [
        ("en-to-hi", "en", "hi", "en"),
        ("hi-to-en", "hi", "en", "hi"),
        ("en-to-hi", "en", "hi", None),
    ],
)
def test_translation_response_accepts_supported_language_metadata(
    direction: str,
    source_language: str,
    target_language: str,
    detected_language: str | None,
) -> None:
    response = TranslationResponse(
        direction=direction,
        source_text="Hello",
        source_language=source_language,
        target_language=target_language,
        detected_language=detected_language,
        translated_text="नमस्ते",
    )

    assert response.status == "success"
    assert response.detected_language == detected_language


def test_translation_response_rejects_languages_that_conflict_with_direction() -> None:
    with pytest.raises(ValidationError, match="source and target languages"):
        TranslationResponse(
            direction="en-to-hi",
            source_text="Hello",
            source_language="hi",
            target_language="en",
            translated_text="नमस्ते",
        )


def test_translation_response_rejects_detected_language_conflicting_with_source() -> None:
    with pytest.raises(ValidationError, match="detected language"):
        TranslationResponse(
            direction="en-to-hi",
            source_text="Hello",
            source_language="en",
            target_language="hi",
            detected_language="hi",
            translated_text="नमस्ते",
        )


def test_error_response_has_a_stable_client_safe_shape() -> None:
    error = ErrorResponse(
        code="translation_failed",
        message="Translation could not be completed.",
        stage="translation",
        request_id="request-id",
    )

    assert error.model_dump() == {
        "status": "error",
        "code": "translation_failed",
        "message": "Translation could not be completed.",
        "stage": "translation",
        "request_id": "request-id",
    }


def test_error_response_rejects_unsupported_stage() -> None:
    with pytest.raises(ValidationError):
        ErrorResponse(
            code="provider_failed",
            message="Provider failed.",
            stage="model-loading",
            request_id="request-id",
        )
