"""Audio upload validation and safe temporary-file helpers."""

from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
import tempfile
import wave
from pathlib import Path

from fastapi import UploadFile

from app.providers.stt import AudioInput

CONTENT_TYPE_SUFFIXES = {
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
}
CONTENT_TYPE_ALIASES = {
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/mp3": "audio/mpeg",
    "audio/x-m4a": "audio/mp4",
    "application/ogg": "audio/ogg",
}
UPLOAD_CHUNK_SIZE = 64 * 1024


class AudioInputError(ValueError):
    """Client-safe invalid-audio error with an HTTP status for API callers."""

    def __init__(self, message: str, *, status_code: int, code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _positive_limit(value: int | float, name: str) -> None:
    if value <= 0 or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError(f"{name} must be greater than zero")


def _normalize_content_type(content_type: str | None) -> str:
    media_type = (
        content_type.split(";", maxsplit=1)[0].strip().lower()
        if content_type
        else ""
    )
    media_type = CONTENT_TYPE_ALIASES.get(media_type, media_type)
    if media_type not in CONTENT_TYPE_SUFFIXES:
        raise AudioInputError(
            "Unsupported audio content type.",
            status_code=415,
            code="unsupported_audio_type",
        )
    return media_type


def _validate_signature(data: bytes, content_type: str) -> None:
    signatures = {
        "audio/flac": data.startswith(b"fLaC"),
        "audio/ogg": data.startswith(b"OggS"),
        "audio/webm": data.startswith(b"\x1a\x45\xdf\xa3"),
        "audio/mp4": len(data) >= 8 and data[4:8] == b"ftyp",
        "audio/mpeg": data.startswith(b"ID3")
        or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0),
    }
    if content_type == "audio/wav":
        signatures[content_type] = (
            data.startswith(b"RIFF") and data[8:12] == b"WAVE"
        )
    if not signatures.get(content_type, False):
        raise AudioInputError(
            "Audio data does not match its declared content type.",
            status_code=415,
            code="unsupported_audio_type",
        )


def audio_duration_seconds(data: bytes, content_type: str) -> float | None:
    """Return WAV duration when available; other supported formats return None."""
    normalized_type = _normalize_content_type(content_type)
    if normalized_type != "audio/wav":
        return None

    try:
        with wave.open(BytesIO(data), "rb") as wav_file:
            if wav_file.getcomptype() != "NONE" or wav_file.getframerate() <= 0:
                raise AudioInputError(
                    "Audio WAV encoding is not supported.",
                    status_code=415,
                    code="unsupported_audio_type",
                )
            frame_count = wav_file.getnframes()
            expected_frame_bytes = (
                frame_count * wav_file.getnchannels() * wav_file.getsampwidth()
            )
            frame_data = wav_file.readframes(frame_count)
            duration = frame_count / wav_file.getframerate()
    except (wave.Error, EOFError) as error:
        raise AudioInputError(
            "Audio WAV data is invalid.",
            status_code=422,
            code="invalid_audio",
        ) from error

    if frame_count == 0:
        raise AudioInputError(
            "Audio data must contain at least one sample.",
            status_code=422,
            code="empty_audio",
        )
    if len(frame_data) != expected_frame_bytes:
        raise AudioInputError(
            "Audio WAV data is truncated.",
            status_code=422,
            code="invalid_audio",
        )
    return duration


def validate_audio_data(
    data: bytes,
    content_type: str | None,
    *,
    max_size_bytes: int,
    max_duration_seconds: float | None = None,
) -> AudioInput:
    """Validate size and media type, returning audio without client filename data."""
    _positive_limit(max_size_bytes, "max_size_bytes")
    if max_duration_seconds is not None:
        _positive_limit(max_duration_seconds, "max_duration_seconds")
    if not data:
        raise AudioInputError(
            "Audio file must not be empty.",
            status_code=422,
            code="empty_audio",
        )
    if len(data) > max_size_bytes:
        raise AudioInputError(
            "Audio file exceeds the configured size limit.",
            status_code=413,
            code="audio_too_large",
        )

    normalized_type = _normalize_content_type(content_type)
    _validate_signature(data, normalized_type)
    duration = audio_duration_seconds(data, normalized_type)
    if duration is not None and max_duration_seconds is not None:
        if duration > max_duration_seconds:
            raise AudioInputError(
                "Audio duration exceeds the configured limit.",
                status_code=413,
                code="audio_too_long",
            )

    return AudioInput(data=data, content_type=normalized_type)


async def read_audio_upload(
    upload: UploadFile,
    *,
    max_size_bytes: int,
    max_duration_seconds: float | None = None,
) -> AudioInput:
    """Read an upload in bounded chunks and close it on every outcome."""
    try:
        _positive_limit(max_size_bytes, "max_size_bytes")
        content_type = _normalize_content_type(upload.content_type)
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = await upload.read(min(UPLOAD_CHUNK_SIZE, max_size_bytes - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > max_size_bytes:
                raise AudioInputError(
                    "Audio file exceeds the configured size limit.",
                    status_code=413,
                    code="audio_too_large",
                )
            chunks.append(chunk)

        return validate_audio_data(
            b"".join(chunks),
            content_type,
            max_size_bytes=max_size_bytes,
            max_duration_seconds=max_duration_seconds,
        )
    finally:
        await upload.close()


@contextmanager
def temporary_audio_file(audio: AudioInput | bytes) -> Iterator[Path]:
    """Write audio to an auto-named temp file and always remove it afterward."""
    if isinstance(audio, AudioInput):
        data = audio.data
        suffix = (
            CONTENT_TYPE_SUFFIXES[_normalize_content_type(audio.content_type)]
            if audio.content_type is not None
            else ".wav"
        )
    else:
        data = audio
        suffix = ".wav"

    if not data:
        raise AudioInputError(
            "Audio file must not be empty.",
            status_code=422,
            code="empty_audio",
        )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(data)
        yield temporary_path
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
