"""Optional faster-whisper adapter; model loading is lazy and isolated."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.providers.stt import (
    AudioInput,
    STTProviderError,
    STTResult,
)
from app.utils.audio import temporary_audio_file


class FasterWhisperSTTProvider:
    """Convert English or Hindi audio using a lazy faster-whisper model."""

    def __init__(
        self,
        model_id: str = "Systran/faster-whisper-small",
        device: str = "auto",
        compute_type: str = "auto",
        cache_dir: str | Path | None = None,
        model_loader: Callable[..., Any] | None = None,
    ) -> None:
        self.model_id = model_id
        self.device = device
        self.compute_type = compute_type
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._model_loader = model_loader
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            if self._model_loader is not None:
                self._model = self._model_loader(
                    self.model_id,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(self.cache_dir) if self.cache_dir else None,
                )
            else:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self.model_id,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(self.cache_dir) if self.cache_dir else None,
                )
        except ImportError as error:
            raise STTProviderError(
                "faster-whisper is not installed; install requirements-ml.txt"
            ) from error
        except Exception as error:
            raise STTProviderError("The STT model could not be loaded") from error

        return self._model

    def _audio_bytes(self, audio: AudioInput | bytes) -> bytes:
        data = audio.data if isinstance(audio, AudioInput) else audio
        if not data:
            raise STTProviderError("Audio input must not be empty")
        return data

    def transcribe(
        self,
        audio: AudioInput | bytes,
        language: str | None = None,
    ) -> STTResult:
        """Transcribe supported English/Hindi audio and return typed metadata."""
        if language not in (None, "en", "hi"):
            raise STTProviderError("STT language must be 'en', 'hi', or unspecified")

        self._audio_bytes(audio)
        try:
            with temporary_audio_file(audio) as temporary_path:
                model = self._load_model()
                segments, info = model.transcribe(
                    str(temporary_path),
                    language=language,
                    task="transcribe",
                )
                segment_list = list(segments)
                transcript = " ".join(
                    str(getattr(segment, "text", "")).strip()
                    for segment in segment_list
                ).strip()
                if not transcript:
                    raise STTProviderError(
                        "The STT provider returned an empty transcript"
                    )

                log_probabilities = [
                    float(segment.avg_logprob)
                    for segment in segment_list
                    if getattr(segment, "avg_logprob", None) is not None
                ]
                confidence = None
                if log_probabilities:
                    confidence = math.exp(
                        sum(log_probabilities) / len(log_probabilities)
                    )
                    confidence = max(0.0, min(1.0, confidence))

                detected_language = getattr(info, "language", language)
                if detected_language not in ("en", "hi"):
                    detected_language = language

                metadata: dict[str, object] = {
                    "provider": "faster-whisper",
                    "model_id": self.model_id,
                    "device": self.device,
                    "compute_type": self.compute_type,
                    "language_probability": getattr(info, "language_probability", None),
                }
                return STTResult(
                    transcript=transcript,
                    language=detected_language,
                    confidence=confidence,
                    metadata=metadata,
                )
        except STTProviderError:
            raise
        except Exception as error:
            raise STTProviderError("Audio transcription failed") from error
