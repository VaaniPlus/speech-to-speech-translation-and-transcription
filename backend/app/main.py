"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

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
from app.schemas.translation import ErrorResponse, ErrorStage
from app.services.speech_to_text_service import SpeechToTextServiceError
from app.services.speech_translation_service import SpeechTranslationServiceError
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

    @application.middleware("http")
    async def attach_request_id(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["null"],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=[
            "X-Transcript",
            "X-Translated-Text",
            "X-Source-Language",
            "X-Target-Language",
            "X-Translation-Direction",
            "Content-Disposition",
            "X-Request-ID",
        ],
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

    def error_response(
        request: Request,
        *,
        status_code: int,
        code: str,
        message: str,
        stage: ErrorStage,
        error: Exception | None = None,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        request_id = request.state.request_id
        if error is not None:
            outcome = "timeout" if code.endswith("_timeout") else "provider_error"
            logger.warning(
                "request_failed request_id=%s outcome=%s stage=%s code=%s "
                "error_type=%s",
                request_id,
                outcome,
                stage,
                code,
                type(error).__name__,
            )
        response_headers = {"X-Request-ID": request_id}
        if headers is not None:
            response_headers.update(headers)
        return JSONResponse(
            status_code=status_code,
            headers=response_headers,
            content=ErrorResponse(
                code=code,
                message=message,
                stage=stage,
                request_id=request_id,
            ).model_dump(),
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del error
        return error_response(
            request,
            status_code=422,
            code="request_validation_failed",
            message="Request validation failed.",
            stage="validation",
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        code = "not_found" if error.status_code == 404 else "http_error"
        message = (
            "The requested resource was not found."
            if error.status_code == 404
            else "The request could not be completed."
        )
        return error_response(
            request,
            status_code=error.status_code,
            code=code,
            message=message,
            stage="unknown",
            headers=error.headers,
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, error: Exception
    ) -> JSONResponse:
        logger.exception(
            "request_failed request_id=%s outcome=unexpected_error stage=unknown",
            request.state.request_id,
            exc_info=(type(error), error, error.__traceback__),
        )
        return error_response(
            request,
            status_code=500,
            code="internal_error",
            message="The request could not be completed.",
            stage="unknown",
        )

    @application.exception_handler(TranslationServiceError)
    async def handle_translation_error(
        request: Request, error: TranslationServiceError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            stage="translation",
            error=error,
        )

    @application.exception_handler(AudioInputError)
    async def handle_audio_input_error(
        request: Request, error: AudioInputError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=str(error),
            stage="validation",
        )

    @application.exception_handler(SpeechToTextServiceError)
    async def handle_speech_to_text_error(
        request: Request, error: SpeechToTextServiceError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            stage="stt",
            error=error,
        )

    @application.exception_handler(SpeechTranslationServiceError)
    async def handle_speech_translation_error(
        request: Request, error: SpeechTranslationServiceError
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            stage=error.stage,
            error=error,
        )

    application.include_router(router, prefix="/api")
    return application


app = create_app()
