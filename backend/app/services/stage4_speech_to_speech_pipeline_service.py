"""End-to-end speech translation orchestration independent of FastAPI."""

from dataclasses import dataclass
import logging
from pathlib import Path
import time

from app.core.logging_config import log_event
from app.providers.stage1_speech_to_text import AudioInput, LanguageCode, STTProvider
from app.providers.stage2_text_to_text_translation import TranslationProvider
from app.providers.stage3_text_to_speech import TTSProvider
from app.schemas.translation import (
    ErrorStage,
    LANGUAGES_BY_DIRECTION,
    TranslationDirection,
    TranslationRequest,
)
from app.services.stage1_speech_to_text_service import (
    SpeechToTextServiceError,
    transcribe_audio,
)
from app.services.stage2_text_to_text_translation_service import (
    TranslationServiceError,
    translate_text,
)
from app.services.stage3_text_to_speech_service import (
    SpeechSynthesisProviderUnavailable,
    SpeechSynthesisServiceError,
    synthesize_text,
)

logger = logging.getLogger(__name__)


class SpeechTranslationServiceError(Exception):
    """A controlled, client-safe failure in an end-to-end speech workflow."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        stage: ErrorStage,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.stage: ErrorStage = stage


class SpeechTranslationProviderUnavailable(SpeechTranslationServiceError):
    """Raised when no TTS provider is configured."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="tts_provider_unavailable",
            message="Speech synthesis is not available because no provider is configured.",
            stage="tts",
        )


class SpeechTranslationFailed(SpeechTranslationServiceError):
    """Raised when the speech translation pipeline cannot complete a stage."""


class SpeechTranslationLanguageMismatch(SpeechTranslationServiceError):
    """Raised when detected speech does not match the requested direction."""

    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="source_language_mismatch",
            message="The detected speech language does not match the selected direction.",
            stage="stt",
        )


@dataclass(frozen=True)
class SpeechTranslationResult:
    """Completed translation metadata and an audio payload or managed file."""

    transcript: str
    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    direction: TranslationDirection
    audio: bytes | Path
    content_type: str


async def translate_speech(
    audio: AudioInput,
    direction: TranslationDirection,
    stt_provider: STTProvider | None,
    translation_provider: TranslationProvider | None,
    tts_provider: TTSProvider | None,
    timeout_seconds: float = 120.0,
) -> SpeechTranslationResult:
    """Transcribe, translate, and synthesize audio for the selected direction."""
    started_at = time.perf_counter()
    source_language, target_language = LANGUAGES_BY_DIRECTION[direction]

    try:
        transcription = await transcribe_audio(
            audio,
            source_language,
            stt_provider,
            timeout_seconds,
        )
    except SpeechToTextServiceError as error:
        raise SpeechTranslationFailed(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            stage="stt",
        ) from error

    if transcription.detected_language != source_language:
        raise SpeechTranslationLanguageMismatch

    try:
        translation = await translate_text(
            TranslationRequest(
                direction=direction,
                source_text=transcription.transcript,
            ),
            translation_provider,
            timeout_seconds,
        )
    except TranslationServiceError as error:
        raise SpeechTranslationFailed(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            stage="translation",
        ) from error

    try:
        synthesis = await synthesize_text(
            translation.translated_text,
            target_language,
            tts_provider,
            timeout_seconds,
            direction=direction,
        )
    except SpeechSynthesisProviderUnavailable as error:
        raise SpeechTranslationProviderUnavailable from error
    except SpeechSynthesisServiceError as error:
        raise SpeechTranslationFailed(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            stage="tts",
        ) from error
    log_event(
        logger,
        logging.INFO,
        "speech_translation_complete",
        outcome="success",
        direction=direction,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
    )
    return SpeechTranslationResult(
        transcript=transcription.transcript,
        translated_text=translation.translated_text,
        source_language=source_language,
        target_language=target_language,
        direction=direction,
        audio=synthesis.audio,
        content_type=synthesis.content_type,
    )
