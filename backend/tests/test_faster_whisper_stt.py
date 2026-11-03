"""Mocked faster-whisper adapter tests; real inference is smoke-only."""

import os
from pathlib import Path

import pytest

from app.providers.faster_whisper_stt import FasterWhisperSTTProvider
from app.providers.stt import AudioInput, STTProviderError, STTResult


class FakeSegment:
    def __init__(self, text: str, avg_logprob: float = -0.2) -> None:
        self.text = text
        self.avg_logprob = avg_logprob


class FakeInfo:
    language = "hi"
    language_probability = 0.98


class FakeWhisperModel:
    def transcribe(self, audio_path: str, language: str | None = None, task: str = "transcribe"):
        assert Path(audio_path).is_file()
        assert task == "transcribe"
        assert language in (None, "en", "hi")
        return iter([FakeSegment("नमस्ते"), FakeSegment("धन्यवाद")]), FakeInfo()


def fake_loader(*args, **kwargs):
    del args, kwargs
    return FakeWhisperModel()


def test_adapter_returns_typed_result_without_loading_ml_package() -> None:
    provider = FasterWhisperSTTProvider(model_loader=fake_loader)

    result = provider.transcribe(
        AudioInput(data=b"test audio", content_type="audio/wav"),
        language="hi",
    )

    assert isinstance(result, STTResult)
    assert result.transcript == "नमस्ते धन्यवाद"
    assert result.language == "hi"
    assert 0.0 <= (result.confidence or 0.0) <= 1.0
    assert result.metadata["provider"] == "faster-whisper"


@pytest.mark.parametrize("fails", [False, True])
def test_adapter_ignores_client_filename_and_cleans_temp_file(fails: bool) -> None:
    temporary_paths: list[Path] = []

    class RecordingModel:
        def transcribe(self, audio_path: str, **kwargs):
            del kwargs
            path = Path(audio_path)
            temporary_paths.append(path)
            assert path.is_file()
            assert path.suffix == ".wav"
            if fails:
                raise RuntimeError("inference failed")
            return iter([FakeSegment("recognized")]), FakeInfo()

    provider = FasterWhisperSTTProvider(model_loader=lambda *args, **kwargs: RecordingModel())
    audio = AudioInput(
        data=b"test audio",
        content_type="audio/wav",
        filename=Path("../../outside.mp3"),
    )

    if fails:
        with pytest.raises(STTProviderError, match="transcription failed"):
            provider.transcribe(audio)
    else:
        assert provider.transcribe(audio).transcript == "recognized"

    assert len(temporary_paths) == 1
    assert "outside" not in temporary_paths[0].name
    assert not temporary_paths[0].exists()


@pytest.mark.parametrize("audio", [b"", AudioInput(data=b"")])
def test_adapter_rejects_empty_audio(audio) -> None:
    provider = FasterWhisperSTTProvider(model_loader=fake_loader)

    with pytest.raises(STTProviderError, match="empty"):
        provider.transcribe(audio)


def test_adapter_rejects_unsupported_language() -> None:
    provider = FasterWhisperSTTProvider(model_loader=fake_loader)

    with pytest.raises(STTProviderError, match="must be"):
        provider.transcribe(b"test audio", language="fr")


def test_adapter_is_lazy_and_reuses_loaded_model() -> None:
    calls = 0

    class CountingLoader:
        def __call__(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            return FakeWhisperModel()

    provider = FasterWhisperSTTProvider(model_loader=CountingLoader())
    provider.transcribe(b"test audio", language="en")
    provider.transcribe(b"test audio again", language="en")

    assert calls == 1


@pytest.mark.skipif(
    os.getenv("RUN_STT_SMOKE") != "1",
    reason="Set RUN_STT_SMOKE=1 and STT_SMOKE_AUDIO_PATH for real local inference",
)
def test_optional_real_stt_smoke() -> None:
    audio_path = os.getenv("STT_SMOKE_AUDIO_PATH")
    if not audio_path:
        pytest.skip("STT_SMOKE_AUDIO_PATH is not set")

    provider = FasterWhisperSTTProvider(device="cpu", compute_type="int8")
    result = provider.transcribe(AudioInput(data=Path(audio_path).read_bytes()))

    assert result.transcript.strip()
    assert result.language in ("en", "hi")
