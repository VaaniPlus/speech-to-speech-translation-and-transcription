"""API router registration."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.config import Settings
from app.providers.stt import LanguageCode, STTProvider
from app.providers.translation import TranslationProvider
from app.providers.tts import TTSProvider
from app.schemas.speech import SpeechToTextResponse
from app.schemas.translation import (
    ErrorResponse,
    LANGUAGES_BY_DIRECTION,
    TranslationDirection,
    TranslationRequest,
    TranslationResponse,
)
from app.services.speech_to_text_service import transcribe_audio
from app.services.speech_translation_service import (
    SpeechTranslationResult,
    translate_speech,
)
from app.services.translation_service import translate_text
from app.utils.audio import CONTENT_TYPE_SUFFIXES, AudioInputError, read_audio_upload

router = APIRouter()


def get_translation_provider(request: Request) -> TranslationProvider | None:
    """Return the provider configured on the application, if any."""
    return getattr(request.app.state, "translation_provider", None)


def get_stt_provider(request: Request) -> STTProvider | None:
    """Return the speech-to-text provider configured on the application."""
    return getattr(request.app.state, "stt_provider", None)


def get_tts_provider(request: Request) -> TTSProvider | None:
    """Return the text-to-speech provider configured on the application."""
    return getattr(request.app.state, "tts_provider", None)


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
    "/speech-translate",
    response_class=Response,
    responses={
        200: {
            "description": (
                "Generated audio file. Transcript and translation are returned "
                "in percent-encoded X-Transcript and X-Translated-Text headers."
            ),
            "headers": {
                "X-Transcript": {
                    "description": "Percent-encoded UTF-8 source transcript.",
                    "schema": {"type": "string"},
                },
                "X-Translated-Text": {
                    "description": "Percent-encoded UTF-8 translated text.",
                    "schema": {"type": "string"},
                },
                "X-Source-Language": {
                    "schema": {"type": "string", "enum": ["en", "hi"]}
                },
                "X-Target-Language": {
                    "schema": {"type": "string", "enum": ["en", "hi"]}
                },
                "X-Translation-Direction": {
                    "schema": {
                        "type": "string",
                        "enum": ["en-to-hi", "hi-to-en"],
                    }
                },
                "Content-Disposition": {
                    "description": "Download filename for generated audio.",
                    "schema": {"type": "string"},
                },
            },
            "content": {
                media_type: {"schema": {"type": "string", "format": "binary"}}
                for media_type in CONTENT_TYPE_SUFFIXES
            },
        },
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
            "description": "Audio or direction validation failed.",
        },
        502: {
            "model": ErrorResponse,
            "description": "A speech processing provider failed.",
        },
        503: {
            "model": ErrorResponse,
            "description": "A speech processing provider is unavailable.",
        },
    },
    tags=["speech"],
    summary="Translate uploaded English or Hindi speech and return synthesized audio",
)
async def speech_translate(
    file: Annotated[
        UploadFile, File(description="English or Hindi source audio file.")
    ],
    direction: Annotated[
        str,
        Form(description="Translation direction: 'en-to-hi' or 'hi-to-en'."),
    ],
    stt_provider: Annotated[STTProvider | None, Depends(get_stt_provider)],
    translation_provider: Annotated[
        TranslationProvider | None,
        Depends(get_translation_provider),
    ],
    tts_provider: Annotated[TTSProvider | None, Depends(get_tts_provider)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Response:
    """Return synthesized audio with transcript and translation in headers."""
    if direction == "en-to-hi":
        validated_direction: TranslationDirection = "en-to-hi"
    elif direction == "hi-to-en":
        validated_direction = "hi-to-en"
    else:
        await file.close()
        raise AudioInputError(
            "Direction must be 'en-to-hi' or 'hi-to-en'.",
            status_code=422,
            code="unsupported_direction",
        )

    audio_input = await read_audio_upload(
        file,
        max_size_bytes=settings.max_upload_size_bytes,
    )
    result = await translate_speech(
        audio_input,
        validated_direction,
        stt_provider,
        translation_provider,
        tts_provider,
    )
    return _speech_translation_file_response(result)


def _speech_translation_file_response(
    result: SpeechTranslationResult,
) -> Response:
    """Build a file-only response; percent-encode text metadata for HTTP headers."""
    headers = {
        "X-Transcript": quote(result.transcript, safe=""),
        "X-Translated-Text": quote(result.translated_text, safe=""),
        "X-Source-Language": result.source_language,
        "X-Target-Language": result.target_language,
        "X-Translation-Direction": result.direction,
        "Access-Control-Expose-Headers": (
            "X-Transcript, X-Translated-Text, X-Source-Language, "
            "X-Target-Language, X-Translation-Direction, Content-Disposition"
        ),
    }
    filename = f"translated-speech{CONTENT_TYPE_SUFFIXES[result.content_type]}"
    if isinstance(result.audio, bytes):
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return Response(
            content=result.audio,
            media_type=result.content_type,
            headers=headers,
        )

    return FileResponse(
        path=result.audio,
        media_type=result.content_type,
        filename=filename,
        headers=headers,
    )


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
