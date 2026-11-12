"""Speech-to-text API success and failure tests using fake providers."""

from io import BytesIO
import time
import wave

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.stt import STTProviderError, STTResult


def wav_bytes() -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8_000)
        wav_file.writeframes(b"\0\0" * 800)
    return output.getvalue()


class FakeSTTProvider:
    def __init__(
        self,
        transcript: str = "Hello there.",
        detected_language: str = "en",
    ) -> None:
        self.calls: list[tuple[str | None, str | None]] = []
        self.transcript = transcript
        self.detected_language = detected_language

    def transcribe(self, audio, language=None) -> STTResult:
        self.calls.append((audio.content_type, language))
        return STTResult(
            transcript=self.transcript,
            language=language or self.detected_language,
            confidence=0.94,
            metadata={"provider": "fake"},
        )


class FailingSTTProvider:
    def transcribe(self, audio, language=None) -> STTResult:
        del audio, language
        raise STTProviderError("private model path and provider details")


class SlowSTTProvider:
    def transcribe(self, audio, language=None) -> STTResult:
        del audio
        time.sleep(0.5)
        return STTResult(transcript="Hello there.", language=language or "en")


@pytest.mark.parametrize(
    ("language", "transcript", "detected_language"),
    [
        ("en", "Hello there.", "en"),
        ("hi", "नमस्ते।", "hi"),
    ],
)
def test_speech_to_text_endpoint_transcribes_supported_languages(
    language: str,
    transcript: str,
    detected_language: str,
) -> None:
    provider = FakeSTTProvider(transcript, detected_language)
    app = create_app(
        Settings(_env_file=None, provider_mode="mock"),
        stt_provider=provider,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("../../client.wav", wav_bytes(), "audio/wav")},
            data={"language": language},
        )

    assert response.status_code == 200
    assert response.json() == {
        "transcript": transcript,
        "requested_language": language,
        "detected_language": detected_language,
        "confidence": 0.94,
        "status": "success",
    }


def test_speech_to_text_endpoint_supports_automatic_language_detection() -> None:
    provider = FakeSTTProvider()
    app = create_app(
        Settings(_env_file=None, provider_mode="mock"),
        stt_provider=provider,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
        )

    assert response.status_code == 200
    assert response.json()["requested_language"] is None
    assert response.json()["detected_language"] == "en"
    assert provider.calls == [("audio/wav", None)]


def test_speech_to_text_endpoint_documents_multipart_and_response_schemas() -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    operation = response.json()["paths"]["/api/speech-to-text"]["post"]
    assert operation["requestBody"]["content"]["multipart/form-data"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/SpeechToTextResponse")
    assert "X-Request-ID" in operation["responses"]["200"]["headers"]
    for status in ("413", "415", "422", "500", "502", "503", "504"):
        assert status in operation["responses"]


@pytest.mark.parametrize(
    ("audio", "content_type", "status_code", "code"),
    [
        (b"", "audio/wav", 422, "empty_audio"),
        (b"not a wav file", "audio/wav", 415, "unsupported_audio_type"),
        (wav_bytes(), "application/octet-stream", 415, "unsupported_audio_type"),
    ],
)
def test_speech_to_text_endpoint_returns_clear_invalid_audio_errors(
    audio: bytes,
    content_type: str,
    status_code: int,
    code: str,
) -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("client.wav", audio, content_type)},
        )

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert response.json()["stage"] == "validation"


def test_speech_to_text_endpoint_enforces_configured_size_limit() -> None:
    data = wav_bytes()
    app = create_app(
        Settings(
            _env_file=None,
            max_upload_size_bytes=len(data) - 1,
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("speech.wav", data, "audio/wav")},
        )

    assert response.status_code == 413
    assert response.json()["code"] == "audio_too_large"


def test_speech_to_text_endpoint_rejects_unsupported_language() -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            data={"language": "fr"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_language"
    assert response.json()["stage"] == "validation"


def test_speech_to_text_endpoint_reports_provider_failure_safely() -> None:
    app = create_app(
        Settings(_env_file=None, provider_mode="mock"),
        stt_provider=FailingSTTProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            data={"language": "hi"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "status": "error",
        "code": "stt_failed",
        "message": "Speech could not be transcribed.",
        "stage": "stt",
        "request_id": response.headers["x-request-id"],
    }
    assert "private model path" not in response.text


def test_speech_to_text_endpoint_reports_missing_provider() -> None:
    app = create_app(Settings(_env_file=None))
    app.state.stt_provider = None

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "stt_provider_unavailable"
    assert response.json()["stage"] == "stt"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_speech_to_text_endpoint_reports_provider_timeout_with_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(
        Settings(
            _env_file=None,
            provider_timeout_seconds=0.1,
        ),
        stt_provider=SlowSTTProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-to-text",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            data={"language": "en"},
        )

    assert response.status_code == 504
    assert response.json()["code"] == "stt_timeout"
    assert response.json()["stage"] == "stt"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    stage_event = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "stage_result"
        and getattr(record, "stage", None) == "stt"
    )
    assert stage_event.outcome == "timeout"
    assert stage_event.request_id == response.headers["x-request-id"]
    assert isinstance(stage_event.duration_ms, float)
