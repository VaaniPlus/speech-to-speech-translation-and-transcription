"""API router registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.core.config import Settings
from app.providers.stt import LanguageCode, STTProvider
from app.providers.translation import TranslationProvider
from app.schemas.speech import SpeechToTextResponse
from app.schemas.translation import (
    ErrorResponse,
    TranslationRequest,
    TranslationResponse,
)
from app.services.speech_to_text_service import transcribe_audio
from app.services.translation_service import translate_text
from app.utils.audio import AudioInputError, read_audio_upload

router = APIRouter()


def get_translation_provider(request: Request) -> TranslationProvider | None:
    """Return the provider configured on the application, if any."""
    return getattr(request.app.state, "translation_provider", None)


def get_stt_provider(request: Request) -> STTProvider | None:
    """Return the speech-to-text provider configured on the application."""
    return getattr(request.app.state, "stt_provider", None)


def get_app_settings(request: Request) -> Settings:
    """Return validated settings configured for this application."""
    return request.app.state.settings


@router.get("/health", tags=["health"], summary="Check API health")
def health_check() -> dict[str, str]:
    """Return the service status without initializing model providers."""
    return {"status": "ok"}


@router.post(
    "/speech-to-text",
    response_model=SpeechToTextResponse,
    responses={
        413: {
            "model": ErrorResponse,
            "description": "Audio upload exceeds a configured limit.",
        },
        415: {
            "model": ErrorResponse,
            "description": "Audio content type is unsupported.",
        },
        422: {
            "model": ErrorResponse,
            "description": "Audio or language validation failed.",
        },
        502: {
            "model": ErrorResponse,
            "description": "Speech-to-text provider failed.",
        },
        503: {
            "model": ErrorResponse,
            "description": "No speech-to-text provider is configured.",
        },
    },
    tags=["speech"],
    summary="Transcribe uploaded English or Hindi audio",
)
async def speech_to_text(
    file: Annotated[
        UploadFile, File(description="English or Hindi audio file.")
    ],
    provider: Annotated[STTProvider | None, Depends(get_stt_provider)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    language: Annotated[
        str | None,
        Form(
            description="Optional language hint: 'en' or 'hi'. Omit for detection."
        ),
    ] = None,
) -> SpeechToTextResponse:
    """Validate an audio upload and return its transcription and language metadata."""
    requested_language: LanguageCode | None = None
    if language == "en":
        requested_language = "en"
    elif language == "hi":
        requested_language = "hi"
    elif language is not None:
        await file.close()
        raise AudioInputError(
            "Language must be 'en' or 'hi'.",
            status_code=422,
            code="unsupported_language",
        )

    audio = await read_audio_upload(
        file,
        max_size_bytes=settings.max_upload_size_bytes,
    )
    return await transcribe_audio(audio, requested_language, provider)


@router.post(
    "/translate",
    response_model=TranslationResponse,
    responses={
        422: {"description": "Request validation failed."},
        502: {"model": ErrorResponse, "description": "Translation provider failed."},
        503: {
            "model": ErrorResponse,
            "description": "No translation provider is configured.",
        },
    },
    tags=["translation"],
    summary="Translate typed text",
)
async def translate(
    payload: TranslationRequest,
    provider: Annotated[
        TranslationProvider | None,
        Depends(get_translation_provider),
    ],
) -> TranslationResponse:
    """Translate non-empty English or Hindi text in the selected direction."""
    return await translate_text(payload, provider)
