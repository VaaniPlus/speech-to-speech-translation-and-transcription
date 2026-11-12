"""Unit tests for typed-text translation orchestration."""

import asyncio
import logging

import pytest

from app.providers.translation import (
    TranslationProviderError,
    TranslationResult,
)
from app.schemas.translation import TranslationRequest
from app.services.translation_service import (
    TranslationFailed,
    TranslationProviderUnavailable,
    translate_text,
)


class FakeProvider:
    def __init__(self, output: str | TranslationResult | Exception) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def translate(self, source_text: str, direction: str):
        self.calls.append((source_text, direction))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


@pytest.mark.parametrize(
    ("direction", "source_text", "output", "source_language", "target_language"),
    [
        ("en-to-hi", "Hello", "नमस्ते", "en", "hi"),
        ("hi-to-en", "नमस्ते", "Hello", "hi", "en"),
    ],
)
def test_translation_service_success_for_both_directions(
    direction: str,
    source_text: str,
    output: str,
    source_language: str,
    target_language: str,
) -> None:
    provider = FakeProvider(output)

    response = asyncio.run(
        translate_text(
            TranslationRequest(direction=direction, source_text=source_text),
            provider,
        )
    )

    assert response.direction == direction
    assert response.source_text == source_text
    assert response.source_language == source_language
    assert response.target_language == target_language
    assert response.translated_text == output
    assert provider.calls == [(source_text, direction)]


def test_translation_service_accepts_typed_provider_result() -> None:
    provider = FakeProvider(
        TranslationResult(
            translated_text="  Hello  ",
            source_language="hi",
            target_language="en",
            metadata={"model_id": "test-model"},
        )
    )

    response = asyncio.run(
        translate_text(
            TranslationRequest(direction="hi-to-en", source_text="नमस्ते"),
            provider,
        )
    )

    assert response.translated_text == "Hello"


def test_translation_service_reports_unavailable_provider() -> None:
    with pytest.raises(TranslationProviderUnavailable):
        asyncio.run(
            translate_text(
                TranslationRequest(direction="en-to-hi", source_text="Hello"),
                None,
            )
        )


def test_translation_service_maps_provider_error() -> None:
    provider = FakeProvider(TranslationProviderError("private model detail"))

    with pytest.raises(TranslationFailed) as error:
        asyncio.run(
            translate_text(
                TranslationRequest(direction="en-to-hi", source_text="Hello"),
                provider,
            )
        )

    assert error.value.status_code == 502
    assert "private model detail" not in str(error.value)


@pytest.mark.parametrize("output", ["", "   ", None])
def test_translation_service_rejects_empty_output(output: object) -> None:
    provider = FakeProvider(output)  # type: ignore[arg-type]

    with pytest.raises(TranslationFailed):
        asyncio.run(
            translate_text(
                TranslationRequest(direction="en-to-hi", source_text="Hello"),
                provider,
            )
        )


def test_translation_service_normalizes_unexpected_exception() -> None:
    provider = FakeProvider(RuntimeError("private runtime detail"))

    with pytest.raises(TranslationFailed) as error:
        asyncio.run(
            translate_text(
                TranslationRequest(direction="hi-to-en", source_text="नमस्ते"),
                provider,
            )
        )

    assert "private runtime detail" not in str(error.value)


def test_translation_service_logs_no_source_text(caplog: pytest.LogCaptureFixture) -> None:
    provider = FakeProvider("नमस्ते")
    private_text = "PRIVATE SOURCE SENTENCE"

    with caplog.at_level(logging.INFO, logger="app.services.translation_service"):
        asyncio.run(
            translate_text(
                TranslationRequest(direction="en-to-hi", source_text=private_text),
                provider,
            )
        )

    assert private_text not in caplog.text
    stage_event = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "stage_result"
    )
    assert stage_event.stage == "translation"
    assert stage_event.outcome == "success"
    assert stage_event.direction == "en-to-hi"
    assert isinstance(stage_event.duration_ms, float)
