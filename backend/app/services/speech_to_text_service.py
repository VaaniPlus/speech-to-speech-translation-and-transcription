"""Speech-to-text orchestration independent of FastAPI."""

import logging
import math
import time

from starlette.concurrency import run_in_threadpool

from app.providers.stt import AudioInput, LanguageCode, STTProvider, STTResult
from app.schemas.speech import SpeechToTextResponse

logger = logging.getLogger(__name__)


class SpeechToTextServiceError(Exception):
    """Base for controlled, client-safe speech-to-text failures."""

    status_code = 502
    code = "stt_failed"
    message = "Speech could not be transcribed."


class STTProviderUnavailable(SpeechToTextServiceError):
    """Raised when no speech-to-text provider is configured."""

    status_code = 503
    code = "stt_provider_unavailable"
    message = "Speech transcription is not available because no provider is configured."


class SpeechToTextFailed(SpeechToTextServiceError):
    """Raised when the provider fails or returns invalid transcription data."""


async def transcribe_audio(
    audio: AudioInput,
    requested_language: LanguageCode | None,
    provider: STTProvider | None,
) -> SpeechToTextResponse:
    """Transcribe validated audio and return safe, typed language metadata."""
    started_at = time.perf_counter()
    if provider is None:
        logger.warning("speech_to_text outcome=provider_unavailable")
        raise STTProviderUnavailable

    try:
        result = await run_in_threadpool(
            provider.transcribe,
            audio,
            requested_language,
        )
    except Exception as error:
        logger.warning(
            "speech_to_text outcome=provider_error error_type=%s",
            type(error).__name__,
        )
        raise SpeechToTextFailed from error

    if not isinstance(result, STTResult):
        logger.warning("speech_to_text outcome=invalid_result result_type=%s", type(result).__name__)
        raise SpeechToTextFailed

    transcript = (
        result.transcript.strip()
        if isinstance(result.transcript, str)
        else ""
    )
    if result.language == "en":
        detected_language: LanguageCode | None = "en"
    elif result.language == "hi":
        detected_language = "hi"
    elif result.language is None:
        detected_language = requested_language
    else:
        detected_language = None

    confidence = result.confidence
    valid_confidence = confidence is None or (
        isinstance(confidence, (int, float))
        and not isinstance(confidence, bool)
        and math.isfinite(confidence)
        and 0.0 <= confidence <= 1.0
    )
    if (
        not transcript
        or detected_language is None
        or not valid_confidence
    ):
        logger.warning("speech_to_text outcome=invalid_result")
        raise SpeechToTextFailed

    response = SpeechToTextResponse(
        transcript=transcript,
        requested_language=requested_language,
        detected_language=detected_language,
        confidence=confidence,
    )
    logger.info(
        "speech_to_text outcome=success requested_language=%s "
        "detected_language=%s duration_ms=%.3f",
        requested_language or "auto",
        detected_language,
        (time.perf_counter() - started_at) * 1000,
    )
    return response
