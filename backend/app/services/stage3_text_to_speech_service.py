"""Text-to-speech orchestration independent of FastAPI."""

from dataclasses import dataclass
import logging
from pathlib import Path
import time

from app.core.logging_config import log_event
from app.providers.stage3_text_to_speech import (
    ManagedAudioArtifact,
    LanguageCode,
    TTSProvider,
    TTSProviderError,
    TTSResult,
)
from app.schemas.translation import TranslationDirection
from app.services.provider_execution import ProviderCallTimeout, run_provider_call
from app.utils.audio import CONTENT_TYPE_SUFFIXES

logger = logging.getLogger(__name__)


class SpeechSynthesisServiceError(Exception):
    """A controlled, client-safe failure in text-to-speech synthesis."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class SpeechSynthesisProviderUnavailable(SpeechSynthesisServiceError):
    """Raised when no TTS provider is configured."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="tts_provider_unavailable",
            message="Speech synthesis is not available because no provider is configured.",
        )


class SpeechSynthesisFailed(SpeechSynthesisServiceError):
    """Raised when a configured provider cannot produce valid audio."""

    def __init__(self) -> None:
        super().__init__(
            status_code=502,
            code="tts_failed",
            message="Speech synthesis could not be completed.",
        )


class SpeechSynthesisTimeout(SpeechSynthesisServiceError):
    """Raised when speech synthesis exceeds its configured timeout."""

    def __init__(self) -> None:
        super().__init__(
            status_code=504,
            code="tts_timeout",
            message="Speech synthesis timed out.",
        )


@dataclass(frozen=True)
class SpeechSynthesisResult:
    """Synthesized audio payload or provider-managed file."""

    audio: bytes | Path
    content_type: str


def _normalize_audio_result(
    result: bytes | TTSResult | ManagedAudioArtifact,
) -> SpeechSynthesisResult:
    if isinstance(result, TTSResult):
        audio: bytes | Path = result.audio_bytes
        content_type = result.content_type
    elif isinstance(result, ManagedAudioArtifact):
        audio = Path(result.uri)
        content_type = result.content_type
        if not audio.is_file() or audio.stat().st_size == 0:
            raise SpeechSynthesisFailed
    elif isinstance(result, bytes):
        audio = result
        content_type = "audio/wav"
    else:
        raise SpeechSynthesisFailed

    if (
        not isinstance(content_type, str)
        or content_type.lower() not in CONTENT_TYPE_SUFFIXES
        or (isinstance(audio, bytes) and not audio)
    ):
        raise SpeechSynthesisFailed
    return SpeechSynthesisResult(audio=audio, content_type=content_type.lower())


async def synthesize_text(
    text: str,
    target_language: LanguageCode,
    provider: TTSProvider | None,
    timeout_seconds: float = 120.0,
    *,
    direction: TranslationDirection | None = None,
) -> SpeechSynthesisResult:
    """Synthesize validated text using the configured provider."""
    started_at = time.perf_counter()
    stage_context: dict[str, object] = {}
    if direction is not None:
        stage_context["direction"] = direction
    if provider is None:
        log_event(
            logger,
            logging.WARNING,
            "stage_result",
            stage="tts",
            outcome="provider_unavailable",
            **stage_context,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        )
        raise SpeechSynthesisProviderUnavailable

    try:
        result = await run_provider_call(
            lambda: provider.synthesize(text, target_language),
            timeout_seconds,
        )
        audio_result = _normalize_audio_result(result)
    except ProviderCallTimeout as error:
        log_event(
            logger,
            logging.WARNING,
            "stage_result",
            stage="tts",
            outcome="timeout",
            **stage_context,
            timeout_seconds=timeout_seconds,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        )
        raise SpeechSynthesisTimeout from error
    except SpeechSynthesisServiceError as error:
        log_event(
            logger,
            logging.WARNING,
            "stage_result",
            stage="tts",
            outcome="invalid_output",
            error_code=error.code,
            **stage_context,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        )
        raise
    except TTSProviderError as error:
        log_event(
            logger,
            logging.WARNING,
            "stage_result",
            stage="tts",
            outcome="provider_error",
            error_type=type(error).__name__,
            **stage_context,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        )
        raise SpeechSynthesisFailed from error
    except Exception as error:
        log_event(
            logger,
            logging.WARNING,
            "stage_result",
            stage="tts",
            outcome="provider_error",
            error_type=type(error).__name__,
            **stage_context,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        )
        raise SpeechSynthesisFailed from error

    log_event(
        logger,
        logging.INFO,
        "stage_result",
        stage="tts",
        outcome="success",
        **stage_context,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
    )
    return audio_result
