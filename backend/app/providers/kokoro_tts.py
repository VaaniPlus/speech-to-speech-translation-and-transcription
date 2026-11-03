"""Lazy Kokoro text-to-speech adapter."""

from __future__ import annotations

import math
import sys
import wave
from array import array
from collections.abc import Callable
from io import BytesIO
from typing import Any

from app.providers.tts import TTSProviderError, TTSResult

LANGUAGE_CONFIGS: dict[str, tuple[str, str]] = {
    "en": ("a", "af_heart"),
    "hi": ("h", "hf_alpha"),
}
SAMPLE_RATE = 24_000


class KokoroTTSProvider:
    """Synthesize English and Hindi WAV audio with lazily loaded Kokoro pipelines."""

    def __init__(
        self,
        en_model_id: str = "hexgrad/Kokoro-82M",
        hi_model_id: str = "hexgrad/Kokoro-82M",
        device: str = "cpu",
        pipeline_loader: Callable[..., Any] | None = None,
    ) -> None:
        self.model_ids = {"en": en_model_id, "hi": hi_model_id}
        self.device = device
        self._pipeline_loader = pipeline_loader
        self._pipelines: dict[str, Any] = {}

    def _load_pipeline(self, language: str) -> Any:
        if language in self._pipelines:
            return self._pipelines[language]

        lang_code, _ = LANGUAGE_CONFIGS[language]
        try:
            if self._pipeline_loader is not None:
                pipeline = self._pipeline_loader(
                    lang_code=lang_code,
                    repo_id=self.model_ids[language],
                    device=self.device,
                )
            else:
                from kokoro import KPipeline

                pipeline = KPipeline(
                    lang_code=lang_code,
                    repo_id=self.model_ids[language],
                    device=self.device,
                )
        except ImportError as error:
            raise TTSProviderError(
                "Kokoro dependencies are not installed; install requirements-ml.txt"
            ) from error
        except Exception as error:
            raise TTSProviderError("The TTS model could not be loaded") from error

        self._pipelines[language] = pipeline
        return pipeline

    @staticmethod
    def _pcm_samples(audio: Any) -> array:
        if hasattr(audio, "detach"):
            audio = audio.detach()
        if hasattr(audio, "cpu"):
            audio = audio.cpu()
        if hasattr(audio, "flatten"):
            audio = audio.flatten()
        if hasattr(audio, "tolist"):
            audio = audio.tolist()
        if not isinstance(audio, (list, tuple)):
            raise TTSProviderError("The TTS provider returned invalid audio data")

        samples = array("h")
        try:
            for sample in audio:
                value = float(sample)
                if not math.isfinite(value):
                    raise ValueError("audio sample is not finite")
                samples.append(round(max(-1.0, min(1.0, value)) * 32767))
        except (TypeError, ValueError, OverflowError) as error:
            raise TTSProviderError(
                "The TTS provider returned invalid audio data"
            ) from error
        return samples

    def synthesize(self, text: str, target_language: str) -> TTSResult:
        """Return synthesized PCM WAV bytes or raise a safe provider error."""
        if target_language not in LANGUAGE_CONFIGS:
            raise TTSProviderError("TTS language must be 'en' or 'hi'")
        if not isinstance(text, str) or not text.strip():
            raise TTSProviderError("TTS text must not be empty")

        lang_code, voice = LANGUAGE_CONFIGS[target_language]
        try:
            pipeline = self._load_pipeline(target_language)
            samples = array("h")
            for chunk in pipeline(text.strip(), voice=voice):
                if not isinstance(chunk, (tuple, list)) or len(chunk) != 3:
                    raise TTSProviderError("The TTS provider returned invalid audio data")
                samples.extend(self._pcm_samples(chunk[2]))
            if not samples:
                raise TTSProviderError("The TTS provider returned no audio")

            if sys.byteorder != "little":
                samples.byteswap()
            output = BytesIO()
            with wave.open(output, "wb") as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(SAMPLE_RATE)
                audio_file.writeframes(samples.tobytes())
        except TTSProviderError:
            raise
        except Exception as error:
            raise TTSProviderError("Text synthesis failed") from error

        return TTSResult(
            audio_bytes=output.getvalue(),
            content_type="audio/wav",
            metadata={
                "provider": "kokoro",
                "model_id": self.model_ids[target_language],
                "voice": voice,
                "sample_rate": SAMPLE_RATE,
            },
        )
