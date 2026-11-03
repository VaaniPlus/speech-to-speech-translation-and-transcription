"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.logging_config import configure_logging
from app.providers.fake import (
    FakeSTTProvider,
    FakeTranslationProvider,
    FakeTTSProvider,
)
from app.providers.faster_whisper_stt import FasterWhisperSTTProvider
from app.providers.indictrans2_translation import IndicTrans2TranslationProvider
from app.providers.kokoro_tts import KokoroTTSProvider
from app.providers.stt import STTProvider
from app.providers.translation import TranslationProvider
from app.providers.tts import TTSProvider
from app.schemas.translation import ErrorResponse
from app.services.speech_to_text_service import SpeechToTextServiceError
from app.services.translation_service import TranslationServiceError
from app.utils.audio import AudioInputError

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    translation_provider: TranslationProvider | None = None,
    stt_provider: STTProvider | None = None,
    tts_provider: TTSProvider | None = None,
) -> FastAPI:
    """Create the API application without loading any speech models."""
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = app_settings
        logger.info("Starting speech translation API")
        try:
            yield
        finally:
            logger.info("Shutting down speech translation API")

    application = FastAPI(
        title="English ↔ Hindi Speech Translation API",
        description="Local-first speech translation and transcription service.",
        version="0.1.0",
        lifespan=lifespan,
    )
    if app_settings.provider_mode == "mock":
        application.state.stt_provider = stt_provider or FakeSTTProvider()
        application.state.translation_provider = (
            translation_provider or FakeTranslationProvider()
        )
        application.state.tts_provider = tts_provider or FakeTTSProvider()
    else:
        application.state.stt_provider = stt_provider or FasterWhisperSTTProvider(
            model_id=app_settings.stt_model_id,
            device=app_settings.device,
            compute_type=app_settings.stt_compute_type,
            cache_dir=app_settings.model_cache_dir,
        )
        application.state.translation_provider = (
            translation_provider
            or IndicTrans2TranslationProvider(
                en_hi_model_id=app_settings.translation_en_hi_model_id,
                hi_en_model_id=app_settings.translation_hi_en_model_id,
                device=app_settings.device,
                cache_dir=app_settings.model_cache_dir,
            )
        )
        application.state.tts_provider = tts_provider or KokoroTTSProvider(
            en_model_id=app_settings.tts_en_model_id,
            hi_model_id=app_settings.tts_hi_model_id,
        )

    @application.exception_handler(TranslationServiceError)
    async def handle_translation_error(
        request: Request, error: TranslationServiceError
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=error.status_code,
            content={
                "status": "error",
                "code": error.code,
                "message": error.message,
                "stage": "translation",
            },
        )

    @application.exception_handler(AudioInputError)
    async def handle_audio_input_error(
        request: Request, error: AudioInputError
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=error.status_code,
            content=ErrorResponse(
                code=error.code,
                message=str(error),
                stage="validation",
            ).model_dump(),
        )

    @application.exception_handler(SpeechToTextServiceError)
    async def handle_speech_to_text_error(
        request: Request, error: SpeechToTextServiceError
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=error.status_code,
            content=ErrorResponse(
                code=error.code,
                message=error.message,
                stage="stt",
            ).model_dump(),
        )

    application.include_router(router, prefix="/api")
    return application


app = create_app()
