"""Speech translation API success and failure tests with fake providers."""

from io import BytesIO
from urllib.parse import unquote
import wave

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.stt import AudioInput, STTProviderError, STTResult
from app.providers.translation import TranslationProviderError
from app.providers.tts import ManagedAudioArtifact, TTSProviderError, TTSResult


def wav_bytes() -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8_000)
        wav_file.writeframes(b"\0\0" * 800)
    return output.getvalue()


class FakeSTTProvider:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events
        self.audio_inputs: list[AudioInput] = []

    def transcribe(self, audio, language=None) -> STTResult:
        assert isinstance(audio, AudioInput)
        self.audio_inputs.append(audio)
        self.events.append(("stt", language))
        transcript = "नमस्ते" if language == "hi" else "Hello there."
        return STTResult(transcript=transcript, language=language, confidence=0.9)


class FakeTranslationProvider:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events

    def translate(self, source_text: str, direction: str) -> str:
        self.events.append(("translation", direction, source_text))
        return "नमस्कार" if direction == "en-to-hi" else "Hello"


class FakeTTSProvider:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events

    def synthesize(self, text: str, target_language: str) -> TTSResult:
        self.events.append(("tts", target_language, text))
        return TTSResult(audio_bytes=b"generated-audio", content_type="audio/wav")


@pytest.mark.parametrize(
    ("direction", "source_language", "target_language", "transcript", "translated"),
    [
        ("en-to-hi", "en", "hi", "Hello there.", "नमस्कार"),
        ("hi-to-en", "hi", "en", "नमस्ते", "Hello"),
    ],
)
def test_speech_translate_returns_audio_file_and_encoded_metadata(
    direction: str,
    source_language: str,
    target_language: str,
    transcript: str,
    translated: str,
) -> None:
    events: list[tuple[object, ...]] = []
    stt_provider = FakeSTTProvider(events)
    app = create_app(
        Settings(_env_file=None, provider_mode="mock"),
        stt_provider=stt_provider,
        translation_provider=FakeTranslationProvider(events),
        tts_provider=FakeTTSProvider(events),
    )

    source_audio = wav_bytes()
    with TestClient(app) as client:
        response = client.post(
            "/api/speech-translate",
            files={"file": ("../../client.wav", source_audio, "audio/wav")},
            data={"direction": direction},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["content-disposition"].endswith(
        'filename="translated-speech.wav"'
    )
    assert response.content == b"generated-audio"
    assert unquote(response.headers["x-transcript"]) == transcript
    assert unquote(response.headers["x-translated-text"]) == translated
    assert response.headers["x-source-language"] == source_language
    assert response.headers["x-target-language"] == target_language
    assert response.headers["x-translation-direction"] == direction
    assert stt_provider.audio_inputs == [
        AudioInput(data=source_audio, content_type="audio/wav")
    ]
    assert events == [
        ("stt", source_language),
        ("translation", direction, transcript),
        ("tts", target_language, translated),
    ]


def test_speech_translate_documents_multipart_binary_response_and_errors() -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        operation = client.get("/openapi.json").json()["paths"][
            "/api/speech-translate"
        ]["post"]

    assert "multipart/form-data" in operation["requestBody"]["content"]
    success = operation["responses"]["200"]
    assert set(success["content"]) == {
        "audio/flac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
    }
    assert success["content"]["audio/wav"]["schema"] == {
        "type": "string",
        "format": "binary",
    }
    assert "X-Transcript" in success["headers"]
    assert "X-Translated-Text" in success["headers"]
    for status in ("413", "415", "422", "502", "503"):
        assert status in operation["responses"]


def test_speech_translate_returns_provider_managed_audio_file(tmp_path) -> None:
    audio_path = tmp_path / "synthesized.wav"
    audio_path.write_bytes(b"provider-managed-audio")

    class ManagedTTSProvider:
        def synthesize(self, text: str, target_language: str) -> ManagedAudioArtifact:
            del text, target_language
            return ManagedAudioArtifact(uri=audio_path)

    app = create_app(
        Settings(_env_file=None, provider_mode="mock"),
        stt_provider=FakeSTTProvider([]),
        translation_provider=FakeTranslationProvider([]),
        tts_provider=ManagedTTSProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-translate",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            data={"direction": "en-to-hi"},
        )

    assert response.status_code == 200
    assert response.content == b"provider-managed-audio"
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["content-disposition"].endswith(
        'filename="translated-speech.wav"'
    )


def test_speech_translate_rejects_unsupported_direction_as_validation_error() -> None:
    app = create_app(Settings(_env_file=None))

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-translate",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            data={"direction": "en-to-fr"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_direction"
    assert response.json()["stage"] == "validation"


class FailingSTTProvider:
    def transcribe(self, audio, language=None) -> STTResult:
        del audio, language
        raise STTProviderError("private STT model details")


class FailingTranslationProvider:
    def translate(self, source_text: str, direction: str) -> str:
        del source_text, direction
        raise TranslationProviderError("private translation details")


class FailingTTSProvider:
    def synthesize(self, text: str, target_language: str) -> TTSResult:
        del text, target_language
        raise TTSProviderError("private TTS model details")


@pytest.mark.parametrize(
    (
        "stt_provider",
        "translation_provider",
        "tts_provider",
        "status",
        "code",
        "stage",
        "private",
    ),
    [
        (
            FailingSTTProvider(),
            FakeTranslationProvider([]),
            FakeTTSProvider([]),
            502,
            "stt_failed",
            "stt",
            "private STT",
        ),
        (
            FakeSTTProvider([]),
            FailingTranslationProvider(),
            FakeTTSProvider([]),
            502,
            "translation_failed",
            "translation",
            "private translation",
        ),
        (
            FakeSTTProvider([]),
            FakeTranslationProvider([]),
            FailingTTSProvider(),
            502,
            "tts_failed",
            "tts",
            "private TTS",
        ),
    ],
)
def test_speech_translate_reports_failed_provider_stage_without_details(
    stt_provider,
    translation_provider,
    tts_provider,
    status: int,
    code: str,
    stage: str,
    private: str,
) -> None:
    app = create_app(
        Settings(_env_file=None, provider_mode="mock"),
        stt_provider=stt_provider,
        translation_provider=translation_provider,
        tts_provider=tts_provider,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-translate",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            data={"direction": "en-to-hi"},
        )

    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["stage"] == stage
    assert private not in response.text


def test_speech_translate_reports_missing_tts_provider() -> None:
    events: list[tuple[object, ...]] = []
    app = create_app(
        Settings(_env_file=None, provider_mode="mock"),
        stt_provider=FakeSTTProvider(events),
        translation_provider=FakeTranslationProvider(events),
    )
    app.state.tts_provider = None

    with TestClient(app) as client:
        response = client.post(
            "/api/speech-translate",
            files={"file": ("speech.wav", wav_bytes(), "audio/wav")},
            data={"direction": "en-to-hi"},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "tts_provider_unavailable"
    assert response.json()["stage"] == "tts"
