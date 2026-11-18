"""Model provider interfaces and controlled provider failures."""

from app.providers.stage1_speech_to_text_faster_whisper import FasterWhisperSTTProvider
from app.providers.stage1_speech_to_text import (
    AudioInput,
    STTProvider,
    STTProviderError,
    STTResult,
)
from app.providers.stage3_text_to_speech_kokoro import KokoroTTSProvider
from app.providers.stage2_text_to_text_translation import (
    TranslationProvider,
    TranslationProviderError,
    TranslationResult,
)
from app.providers.stage3_text_to_speech import (
    ManagedAudioArtifact,
    TTSProvider,
    TTSProviderError,
    TTSResult,
)

__all__ = [
    "AudioInput",
    "FasterWhisperSTTProvider",
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
