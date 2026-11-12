"""API route registration tests."""

import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.translation import TranslationDirection, TranslationProviderError


class FakeTranslationProvider:
    """Deterministic provider for endpoint tests."""

    def translate(self, source_text: str, direction: TranslationDirection) -> str:
        return f"{direction}: {source_text}"


class FailingTranslationProvider:
    """Provider test double that simulates a controlled inference failure."""

    def translate(self, source_text: str, direction: TranslationDirection) -> str:
        del source_text, direction
        raise TranslationProviderError("internal provider details")


class SlowTranslationProvider:
    def translate(self, source_text: str, direction: TranslationDirection) -> str:
        del source_text, direction
        time.sleep(0.2)
        return "नमस्ते"


def test_health_endpoint_is_documented_in_openapi() -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
    openapi = response.json()
    assert "/api/translate" in openapi["paths"]
    operation = openapi["paths"]["/api/translate"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/TranslationRequest")
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/TranslationResponse")
    assert "X-Request-ID" in operation["responses"]["200"]["headers"]
    assert "422" in operation["responses"]
    assert "500" in operation["responses"]
    assert "502" in operation["responses"]
    assert "503" in operation["responses"]
    assert "504" in operation["responses"]


@pytest.mark.parametrize(
    ("direction", "source_text", "source_language", "target_language"),
    [
        ("en-to-hi", "Hello", "en", "hi"),
        ("hi-to-en", "नमस्ते", "hi", "en"),
    ],
)
def test_translate_endpoint_returns_typed_translation(
    direction: str,
    source_text: str,
    source_language: str,
    target_language: str,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        translation_provider=FakeTranslationProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": direction, "source_text": source_text},
        )

    assert response.status_code == 200
    assert response.json() == {
        "direction": direction,
        "source_text": source_text,
        "source_language": source_language,
        "target_language": target_language,
        "detected_language": None,
        "translated_text": f"{direction}: {source_text}",
        "status": "success",
    }


@pytest.mark.parametrize("source_text", ["", " ", "\t\n"])
def test_translate_endpoint_returns_useful_422_for_empty_text(
    source_text: str,
) -> None:
    app = create_app(
        Settings(_env_file=None),
        translation_provider=FakeTranslationProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": "en-to-hi", "source_text": source_text},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_failed"
    assert response.json()["message"] == "Request validation failed."
    assert response.json()["stage"] == "validation"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_translate_endpoint_rejects_unsupported_direction() -> None:
    app = create_app(
        Settings(_env_file=None),
        translation_provider=FakeTranslationProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": "en-to-fr", "source_text": "Hello"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_failed"
    assert response.json()["stage"] == "validation"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_translate_endpoint_reports_unconfigured_provider_safely() -> None:
    app = create_app(Settings(_env_file=None))
    app.state.translation_provider = None

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": "en-to-hi", "source_text": "Hello"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "code": "translation_provider_unavailable",
        "message": "Translation is not available because no provider is configured.",
        "stage": "translation",
        "request_id": response.headers["x-request-id"],
    }


def test_translate_endpoint_reports_real_provider_load_failure_safely() -> None:
    app = create_app(Settings(_env_file=None, provider_mode="real"))

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": "en-to-hi", "source_text": "Hello"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "status": "error",
        "code": "translation_failed",
        "message": "Translation could not be completed.",
        "stage": "translation",
        "request_id": response.headers["x-request-id"],
    }


def test_translate_endpoint_reports_provider_failure_without_internal_details() -> None:
    app = create_app(
        Settings(_env_file=None),
        translation_provider=FailingTranslationProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": "en-to-hi", "source_text": "Hello"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "status": "error",
        "code": "translation_failed",
        "message": "Translation could not be completed.",
        "stage": "translation",
        "request_id": response.headers["x-request-id"],
    }
    assert "internal provider details" not in response.text


def test_translate_endpoint_reports_provider_timeout_with_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            provider_timeout_seconds=0.1,
        ),
        translation_provider=SlowTranslationProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": "en-to-hi", "source_text": "Hello"},
        )

    assert response.status_code == 504
    assert response.json()["code"] == "translation_timeout"
    assert response.json()["stage"] == "translation"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    stage_event = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "stage_result"
        and getattr(record, "stage", None) == "translation"
    )
    assert stage_event.outcome == "timeout"
    assert stage_event.request_id == response.headers["x-request-id"]
    assert isinstance(stage_event.duration_ms, float)
