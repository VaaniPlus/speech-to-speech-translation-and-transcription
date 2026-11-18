"""Development/mock provider tests."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.fake_providers import FakeSTTProvider, FakeTTSProvider, FakeTranslationProvider
from app.providers.stage1_speech_to_text_faster_whisper import FasterWhisperSTTProvider
from app.providers.stage2_text_to_text_translation_indictrans2 import IndicTrans2TranslationProvider
from app.providers.stage2_text_to_text_translation_marian import MarianTranslationProvider
from app.providers.stage3_text_to_speech_kokoro import KokoroTTSProvider
from app.providers.stage1_speech_to_text import AudioInput


def test_fake_providers_are_deterministic_and_marked_as_mock_output() -> None:
    stt = FakeSTTProvider()
    translation = FakeTranslationProvider()
    tts = FakeTTSProvider()

    stt_result = stt.transcribe(AudioInput(data=b"test audio"), language="hi")
    assert stt_result.transcript == "[mock transcription]"
    assert stt_result.metadata == {"provider": "fake", "real_model": False}

    assert translation.translate("Hello", "en-to-hi") == "[mock en-to-hi] Hello"

    tts_result = tts.synthesize("Hello", "hi")
    assert tts_result.metadata == {"provider": "fake", "real_model": False}
    assert b"MOCK" in tts_result.audio_bytes


def test_mock_mode_is_configurable_and_installs_fake_providers() -> None:
    app = create_app(Settings(_env_file=None, provider_mode="mock"))

    assert isinstance(app.state.stt_provider, FakeSTTProvider)
    assert isinstance(app.state.translation_provider, FakeTranslationProvider)
    assert isinstance(app.state.tts_provider, FakeTTSProvider)

    with TestClient(app) as client:
        response = client.post(
            "/api/translate",
            json={"direction": "en-to-hi", "source_text": "Hello"},
        )

    assert response.status_code == 200
    assert response.json()["translated_text"] == "[mock en-to-hi] Hello"
    assert "real translation" not in response.text.lower()


def test_real_mode_installs_real_adapters_without_fake_providers() -> None:
    app = create_app(Settings(_env_file=None, provider_mode="real"))

    assert isinstance(app.state.stt_provider, FasterWhisperSTTProvider)
    assert isinstance(app.state.translation_provider, MarianTranslationProvider)
    assert isinstance(app.state.tts_provider, KokoroTTSProvider)


def test_real_mode_can_select_indictrans2_explicitly() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            provider_mode="real",
            translation_provider="indictrans2",
        )
    )

    assert isinstance(app.state.translation_provider, IndicTrans2TranslationProvider)
