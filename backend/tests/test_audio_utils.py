"""Tests for bounded audio upload validation and temporary-file handling."""

import asyncio
from io import BytesIO
import wave

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.providers.stt import AudioInput
from app.utils.audio import (
    AudioInputError,
    audio_duration_seconds,
    read_audio_upload,
    temporary_audio_file,
    validate_audio_data,
)


def wav_bytes(*, duration_seconds: float = 0.25, sample_rate: int = 8_000) -> bytes:
    frame_count = int(duration_seconds * sample_rate)
    output = BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\0\0" * frame_count)
    return output.getvalue()


def make_upload(data: bytes, filename: str, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_validates_wav_and_returns_duration() -> None:
    data = wav_bytes()

    audio = validate_audio_data(data, "audio/wav; codecs=1", max_size_bytes=len(data))

    assert audio == AudioInput(data=data, content_type="audio/wav")
    assert audio.filename is None
    assert audio_duration_seconds(data, "audio/wav") == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("data", "content_type"),
    [
        (b"", "audio/wav"),
        (wav_bytes(), "application/octet-stream"),
        (wav_bytes(), "audio/mpeg"),
        (b"RIFF\x00\x00\x00\x00WAVE", "audio/wav"),
    ],
)
def test_rejects_empty_unsupported_or_malformed_audio(
    data: bytes,
    content_type: str,
) -> None:
    with pytest.raises(AudioInputError):
        validate_audio_data(data, content_type, max_size_bytes=1024)


def test_enforces_configured_maximum_upload_size() -> None:
    data = wav_bytes()

    with pytest.raises(AudioInputError) as error:
        validate_audio_data(data, "audio/wav", max_size_bytes=len(data) - 1)

    assert error.value.status_code == 413
    assert error.value.code == "audio_too_large"


def test_enforces_optional_wav_duration_limit() -> None:
    data = wav_bytes(duration_seconds=0.5)

    with pytest.raises(AudioInputError) as error:
        validate_audio_data(
            data,
            "audio/wav",
            max_size_bytes=len(data),
            max_duration_seconds=0.25,
        )

    assert error.value.status_code == 413
    assert error.value.code == "audio_too_long"


def test_reads_upload_in_bounded_chunks_and_closes_it() -> None:
    data = wav_bytes()
    upload = make_upload(data, "../../outside.wav", "audio/x-wav")

    audio = asyncio.run(read_audio_upload(upload, max_size_bytes=len(data)))

    assert audio.data == data
    assert audio.content_type == "audio/wav"
    assert audio.filename is None
    assert upload.file.closed


def test_oversized_upload_is_rejected_and_closed() -> None:
    data = wav_bytes()
    upload = make_upload(data, "speech.wav", "audio/wav")

    with pytest.raises(AudioInputError) as error:
        asyncio.run(read_audio_upload(upload, max_size_bytes=len(data) - 1))

    assert error.value.status_code == 413
    assert upload.file.closed


def test_unsupported_upload_is_rejected_and_closed() -> None:
    upload = make_upload(b"data", "speech.bin", "application/octet-stream")

    with pytest.raises(AudioInputError) as error:
        asyncio.run(read_audio_upload(upload, max_size_bytes=1024))

    assert error.value.status_code == 415
    assert upload.file.closed


def test_temporary_audio_file_ignores_filename_and_cleans_up_on_success() -> None:
    audio = AudioInput(
        data=b"audio",
        content_type="audio/wav",
        filename="../../outside.mp3",
    )

    with temporary_audio_file(audio) as path:
        assert path.is_file()
        assert path.suffix == ".wav"
        assert "outside" not in path.name
    assert not path.exists()


def test_temporary_audio_file_cleans_up_on_failure() -> None:
    path = None
    with pytest.raises(RuntimeError, match="inference failed"):
        with temporary_audio_file(b"audio") as temporary_path:
            path = temporary_path
            raise RuntimeError("inference failed")

    assert path is not None
    assert not path.exists()
