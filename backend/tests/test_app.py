"""Tests for FastAPI application initialization."""

import logging

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app


def test_app_exposes_openapi_docs_and_api_router() -> None:
    app = create_app(Settings(_env_file=None))

    assert app.title == "English ↔ Hindi Speech Translation API"
    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"
    assert app.router.routes


def test_app_lifespan_starts_and_shuts_down_without_loading_models() -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.get("/docs")

        assert response.status_code == 200
        assert app.state.settings.device == "auto"
        assert not hasattr(app.state, "models")


@pytest.mark.parametrize(
    "origin",
    ["null", "http://127.0.0.1:5500", "http://localhost:3000"],
)
def test_app_allows_local_browser_origins_and_exposes_speech_metadata(
    origin: str,
) -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.options(
            "/api/speech-translate",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        metadata_response = client.get(
            "/api/health",
            headers={"Origin": origin},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]
    assert metadata_response.headers["access-control-allow-origin"] == origin
    assert "X-Transcript" in metadata_response.headers["access-control-expose-headers"]
    assert "X-Translated-Text" in metadata_response.headers["access-control-expose-headers"]
    assert "X-Request-ID" in metadata_response.headers["access-control-expose-headers"]
    assert metadata_response.headers["x-request-id"]


def test_app_does_not_allow_arbitrary_browser_origins() -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.get(
            "/api/health",
            headers={"Origin": "https://example.com"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_unexpected_error_returns_safe_correlated_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(Settings(_env_file=None))

    def fail() -> None:
        raise RuntimeError("C:\\private\\models\\secret")

    app.add_api_route("/test-error", fail)

    with caplog.at_level(logging.ERROR, logger="app.main"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/test-error")

    assert response.status_code == 500
    assert response.json() == {
        "status": "error",
        "code": "internal_error",
        "message": "The request could not be completed.",
        "stage": "unknown",
        "request_id": response.headers["x-request-id"],
    }
    assert "C:\\private\\models\\secret" not in response.text
    assert f"request_id={response.headers['x-request-id']}" in caplog.text
