"""End-to-end speech translation orchestration independent of FastAPI."""

from dataclasses import dataclass
import logging
from pathlib import Path
import time

from starlette.concurrency import run_in_threadpool

from app.providers.stt import AudioInput, LanguageCode, STTProvider
from app.providers.translation import TranslationProvider
from app.providers.tts import (
    ManagedAudioArtifact,
    TTSProvider,
    TTSProviderError,
    TTSResult,
)
from app.schemas.translation import (
    LANGUAGES_BY_DIRECTION,
    TranslationDirection,
    TranslationRequest,
)
from app.services.speech_to_text_service import (
    SpeechToTextServiceError,
    transcribe_audio,
)
from app.services.translation_service import (
    TranslationServiceError,
    translate_text,
)
from app.utils.audio import CONTENT_TYPE_SUFFIXES

logger = logging.getLogger(__name__)


class SpeechTranslationServiceError(Exception):
    """A controlled, client-safe failure in an end-to-end speech workflow."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        stage: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.stage = stage


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


def _normalize_audio_result(
    result: bytes | TTSResult | ManagedAudioArtifact,
) -> tuple[bytes | Path, str]:
    if isinstance(result, TTSResult):
        audio: bytes | Path = result.audio_bytes
        content_type = result.content_type
    elif isinstance(result, ManagedAudioArtifact):
        audio = Path(result.uri)
        content_type = result.content_type
        if not audio.is_file() or audio.stat().st_size == 0:
            raise SpeechTranslationFailed(
                status_code=502,
                code="tts_failed",
                message="Speech synthesis could not be completed.",
                stage="tts",
            )
    elif isinstance(result, bytes):
        audio = result
        content_type = "audio/wav"
    else:
        raise SpeechTranslationFailed(
            status_code=502,
            code="tts_failed",
            message="Speech synthesis could not be completed.",
            stage="tts",
        )

    if (
        not isinstance(content_type, str)
        or content_type.lower() not in CONTENT_TYPE_SUFFIXES
        or (isinstance(audio, bytes) and not audio)
    ):
        raise SpeechTranslationFailed(
            status_code=502,
            code="tts_failed",
            message="Speech synthesis could not be completed.",
            stage="tts",
        )
    return audio, content_type.lower()


async def translate_speech(
    audio: AudioInput,
    direction: TranslationDirection,
    stt_provider: STTProvider | None,
    translation_provider: TranslationProvider | None,
    tts_provider: TTSProvider | None,
) -> SpeechTranslationResult:
    """Transcribe, translate, and synthesize audio for the selected direction."""
    started_at = time.perf_counter()
    source_language, target_language = LANGUAGES_BY_DIRECTION[direction]

    try:
        transcription = await transcribe_audio(audio, source_language, stt_provider)
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
        )
    except TranslationServiceError as error:
        raise SpeechTranslationFailed(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            stage="translation",
        ) from error

    if tts_provider is None:
        logger.warning("speech_translation outcome=tts_provider_unavailable")
        raise SpeechTranslationProviderUnavailable

    try:
        tts_result = await run_in_threadpool(
            tts_provider.synthesize,
            translation.translated_text,
            target_language,
        )
        generated_audio, content_type = _normalize_audio_result(tts_result)
    except SpeechTranslationServiceError:
        raise
    except TTSProviderError as error:
        logger.warning(
            "speech_translation outcome=tts_provider_error error_type=%s",
            type(error).__name__,
        )
        raise SpeechTranslationFailed(
            status_code=502,
            code="tts_failed",
            message="Speech synthesis could not be completed.",
            stage="tts",
        ) from error
    except Exception as error:
        logger.warning(
            "speech_translation outcome=tts_unexpected_error error_type=%s",
            type(error).__name__,
        )
        raise SpeechTranslationFailed(
            status_code=502,
            code="tts_failed",
            message="Speech synthesis could not be completed.",
            stage="tts",
        ) from error

    if isinstance(generated_audio, bytes) and not generated_audio:
        raise SpeechTranslationFailed(
            status_code=502,
            code="tts_failed",
            message="Speech synthesis could not be completed.",
            stage="tts",
        )

    logger.info(
        "speech_translation outcome=success direction=%s duration_ms=%.3f",
        direction,
        (time.perf_counter() - started_at) * 1000,
    )
    return SpeechTranslationResult(
        transcript=transcription.transcript,
        translated_text=translation.translated_text,
        source_language=source_language,
        target_language=target_language,
        direction=direction,
        audio=generated_audio,
        content_type=content_type,
    )
