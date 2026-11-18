"""Typed text-to-speech provider boundary."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

LanguageCode = Literal["en", "hi"]


@dataclass(frozen=True)
class ManagedAudioArtifact:
    """A provider-managed audio path or artifact reference."""

    uri: str | Path
    content_type: str = "audio/wav"
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TTSResult:
    """In-memory synthesized audio and its format metadata."""

    audio_bytes: bytes
    content_type: str = "audio/wav"
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def audio(self) -> bytes:
        """Compatibility alias for the synthesized bytes."""
        return self.audio_bytes


TTSAudio = TTSResult | ManagedAudioArtifact | bytes


class TTSProviderError(Exception):
    """Expected failure raised by a TTS provider."""


@runtime_checkable
class TTSProvider(Protocol):
    """Synthesize text in a requested language without loading an ML package here."""

    def synthesize(
        self,
        text: str,
        target_language: LanguageCode | str,
    ) -> TTSAudio:
        """Return audio bytes or a managed artifact or raise ``TTSProviderError``."""
