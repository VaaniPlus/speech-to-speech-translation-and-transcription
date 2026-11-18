"""Tests for injectable provider boundaries."""

import asyncio

from app.providers import (
    ManagedAudioArtifact,
    STTProvider,
    STTProviderError,
    STTResult,
    TTSProvider,
    TTSProviderError,
    TTSResult,
    TranslationProvider,
    TranslationProviderError,
    TranslationResult,
)
from app.providers.stage1_speech_to_text import AudioInput
from app.schemas.translation import TranslationRequest
from app.services.stage2_text_to_text_translation_service import translate_text


class FakeSTTProvider:
    def transcribe(self, audio, language=None) -> STTResult:
        return STTResult(
            transcript="नमस्ते",
            language="hi",
            confidence=0.99,
            metadata={"model": "fake"},
        )


class FakeTranslationProvider:
    def translate(self, source_text, direction) -> TranslationResult:
        return TranslationResult(
            translated_text="नमस्ते",
            source_language="en",
            target_language="hi",
        )


class FakeTTSProvider:
    def synthesize(self, text, target_language) -> TTSResult:
        return TTSResult(audio_bytes=b"RIFFfake", content_type="audio/wav")


def test_provider_protocols_accept_structural_fake_implementations() -> None:
    stt: STTProvider = FakeSTTProvider()
    translation: TranslationProvider = FakeTranslationProvider()
    tts: TTSProvider = FakeTTSProvider()

    result = stt.transcribe(AudioInput(data=b"audio", content_type="audio/wav"))
    assert result.transcript == "नमस्ते"
    assert result.detected_language == "hi"

    translated = translation.translate("Hello", "en-to-hi")
    assert translated.translated_text == "नमस्ते"

    synthesized = tts.synthesize("नमस्ते", "hi")
    assert synthesized.audio_bytes == b"RIFFfake"


def test_managed_audio_artifact_is_a_typed_tts_return() -> None:
    artifact = ManagedAudioArtifact(uri="generated/hello.wav", content_type="audio/wav")

    class ArtifactTTSProvider:
        def synthesize(self, text, target_language):
            return artifact

    provider: TTSProvider = ArtifactTTSProvider()
    assert provider.synthesize("Hello", "en") is artifact


def test_translation_service_accepts_typed_fake_translation_result() -> None:
    response = asyncio.run(
        translate_text(
            TranslationRequest(direction="en-to-hi", source_text="Hello"),
            FakeTranslationProvider(),
        )
    )

    assert response.translated_text == "नमस्ते"


def test_provider_errors_are_separate_domain_exceptions() -> None:
    assert issubclass(STTProviderError, Exception)
    assert issubclass(TTSProviderError, Exception)
    assert issubclass(TranslationProviderError, Exception)
