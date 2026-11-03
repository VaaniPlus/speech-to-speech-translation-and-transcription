"""Model provider interfaces and controlled provider failures."""

from app.providers.faster_whisper_stt import FasterWhisperSTTProvider
from app.providers.stt import (
    AudioInput,
    STTProvider,
    STTProviderError,
    STTResult,
)
from app.providers.indictrans2_translation import IndicTrans2TranslationProvider
from app.providers.kokoro_tts import KokoroTTSProvider
from app.providers.translation import (
    TranslationProvider,
    TranslationProviderError,
    TranslationResult,
)
from app.providers.tts import (
    ManagedAudioArtifact,
    TTSProvider,
    TTSProviderError,
    TTSResult,
)

__all__ = [
    "AudioInput",
    "FasterWhisperSTTProvider",
    "IndicTrans2TranslationProvider",
    "KokoroTTSProvider",
    "ManagedAudioArtifact",
    "STTProvider",
    "STTProviderError",
    "STTResult",
    "TTSProvider",
    "TTSProviderError",
    "TTSResult",
    "TranslationProvider",
    "TranslationProviderError",
    "TranslationResult",
]
