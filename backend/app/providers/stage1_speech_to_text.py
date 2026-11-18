"""Typed speech-to-text provider boundary."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

LanguageCode = Literal["en", "hi"]


@dataclass(frozen=True)
class AudioInput:
    """Audio data and the optional metadata needed by an STT provider."""

    data: bytes
    content_type: str | None = None
    filename: str | Path | None = None


@dataclass(frozen=True)
class STTResult:
    """A transcription and provider-reported language metadata."""

    transcript: str
    language: LanguageCode | str | None = None
    confidence: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Compatibility alias for consumers that call the transcript text."""
        return self.transcript

    @property
    def detected_language(self) -> LanguageCode | str | None:
        """Compatibility alias for the detected or requested language."""
        return self.language


class STTProviderError(Exception):
    """Expected failure raised by an STT provider."""


@runtime_checkable
class STTProvider(Protocol):
    """Transcribe audio without exposing a concrete model implementation."""

    def transcribe(
        self,
        audio: AudioInput | bytes,
        language: LanguageCode | str | None = None,
    ) -> STTResult:
        """Return a typed transcript or raise ``STTProviderError``."""
