"""Typed-text translation orchestration independent of FastAPI."""

import logging
import time

from app.providers.translation import (
    TranslationProvider,
    TranslationProviderError,
    TranslationResult,
)
from app.services.provider_execution import ProviderCallTimeout, run_provider_call
from app.schemas.translation import (
    LANGUAGES_BY_DIRECTION,
    TranslationRequest,
    TranslationResponse,
)


class TranslationServiceError(Exception):
    """Base for expected, client-safe translation service failures."""

    status_code = 502
    code = "translation_failed"
    message = "Translation could not be completed."


class TranslationProviderUnavailable(TranslationServiceError):
    """Raised when no translation provider is configured."""

    status_code = 503
    code = "translation_provider_unavailable"
    message = "Translation is not available because no provider is configured."


class TranslationFailed(TranslationServiceError):
    """Raised when a configured provider cannot produce a translation."""


class TranslationTimeout(TranslationServiceError):
    """Raised when translation exceeds its configured timeout."""

    status_code = 504
    code = "translation_timeout"
    message = "Translation timed out."


logger = logging.getLogger(__name__)


async def translate_text(
    request: TranslationRequest,
    provider: TranslationProvider | None,
    timeout_seconds: float = 120.0,
) -> TranslationResponse:
    """Translate validated text using the configured provider."""
    started_at = time.perf_counter()
    if provider is None:
        logger.warning(
            "translation service outcome=provider_unavailable direction=%s duration_ms=%.3f",
            request.direction,
            (time.perf_counter() - started_at) * 1000,
        )
        raise TranslationProviderUnavailable

    try:
        translated_text = await run_provider_call(
            lambda: provider.translate(request.source_text, request.direction),
            timeout_seconds,
        )
    except ProviderCallTimeout as error:
        logger.warning(
            "translation service outcome=timeout direction=%s "
            "timeout_seconds=%.3f",
            request.direction,
            timeout_seconds,
        )
        raise TranslationTimeout from error
    except TranslationProviderError as error:
        logger.warning(
            "translation service outcome=provider_error direction=%s duration_ms=%.3f error_type=%s",
            request.direction,
            (time.perf_counter() - started_at) * 1000,
            type(error).__name__,
        )
        raise TranslationFailed from error
    except Exception as error:
        logger.warning(
            "translation service outcome=unexpected_provider_error direction=%s duration_ms=%.3f error_type=%s",
            request.direction,
            (time.perf_counter() - started_at) * 1000,
            type(error).__name__,
        )
        raise TranslationFailed from error

    if isinstance(translated_text, TranslationResult):
        translated_text = translated_text.translated_text

    if not isinstance(translated_text, str) or not translated_text.strip():
        logger.warning(
            "translation service outcome=empty_output direction=%s duration_ms=%.3f",
            request.direction,
            (time.perf_counter() - started_at) * 1000,
        )
        raise TranslationFailed

    source_language, target_language = LANGUAGES_BY_DIRECTION[request.direction]
    response = TranslationResponse(
        direction=request.direction,
        source_text=request.source_text,
        source_language=source_language,
        target_language=target_language,
        translated_text=translated_text.strip(),
    )
    logger.info(
        "translation service outcome=success direction=%s duration_ms=%.3f",
        request.direction,
        (time.perf_counter() - started_at) * 1000,
    )
    return response
