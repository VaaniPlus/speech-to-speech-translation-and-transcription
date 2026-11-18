"""Development/test-only deterministic providers; never claim mock output is real."""

from app.providers.stage1_speech_to_text import AudioInput, STTResult
from app.providers.stage3_text_to_speech import TTSResult


class FakeSTTProvider:
    """Development/test-only STT provider with deterministic local behavior."""

    def transcribe(
        self,
        audio: AudioInput | bytes,
        language: str | None = None,
    ) -> STTResult:
        del audio
        return STTResult(
            transcript="[mock transcription]",
            language=language or "en",
            confidence=1.0,
            metadata={"provider": "fake", "real_model": False},
        )


class FakeTranslationProvider:
    """Development/test-only translation provider with deterministic local behavior."""

    def translate(self, source_text: str, direction: str) -> str:
        return f"[mock {direction}] {source_text}"


class FakeTTSProvider:
    """Development/test-only TTS provider; output is not usable speech audio."""

    def synthesize(self, text: str, target_language: str) -> TTSResult:
        del text, target_language
        return TTSResult(
            audio_bytes=b"MOCK_AUDIO_NOT_REAL_SPEECH",
            content_type="audio/wav",
            metadata={"provider": "fake", "real_model": False},
        )
