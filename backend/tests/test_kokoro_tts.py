"""Unit tests for the lazy Kokoro text-to-speech adapter."""

from io import BytesIO
import wave

import pytest

from app.providers.kokoro_tts import KokoroTTSProvider
from app.providers.tts import TTSProviderError, TTSResult


class FakeAudio:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def detach(self):
        return self

    def cpu(self):
        return self

    def flatten(self):
        return self

    def tolist(self) -> list[float]:
        return self.values


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, text: str, voice: str):
        self.calls.append((text, voice))
        yield "graphemes", "phonemes", FakeAudio([0.0, 0.5, -0.5])
        yield "more graphemes", "more phonemes", FakeAudio([1.0])


@pytest.mark.parametrize(
    ("language", "lang_code", "voice"),
    [("en", "a", "af_heart"), ("hi", "h", "hf_alpha")],
)
def test_synthesizes_valid_wav_for_supported_languages(
    language: str,
    lang_code: str,
    voice: str,
) -> None:
    pipeline = FakePipeline()
    loader_calls: list[dict[str, str]] = []

    def pipeline_loader(**kwargs):
        loader_calls.append(kwargs)
        return pipeline

    provider = KokoroTTSProvider(pipeline_loader=pipeline_loader)

    result = provider.synthesize("  hello नमस्ते  ", language)

    assert isinstance(result, TTSResult)
    assert result.content_type == "audio/wav"
    assert result.audio_bytes.startswith(b"RIFF")
    assert loader_calls == [
        {
            "lang_code": lang_code,
            "repo_id": "hexgrad/Kokoro-82M",
            "device": "cpu",
        }
    ]
    assert pipeline.calls == [("hello नमस्ते", voice)]
    assert result.metadata["voice"] == voice
    with wave.open(BytesIO(result.audio_bytes), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 24_000
        assert wav.getnframes() == 4


@pytest.mark.parametrize("text", ["", "  ", None])
def test_rejects_empty_or_invalid_text(text) -> None:
    provider = KokoroTTSProvider(pipeline_loader=lambda **kwargs: None)

    with pytest.raises(TTSProviderError, match="text must not be empty"):
        provider.synthesize(text, "en")


def test_rejects_unsupported_language_before_loading_pipeline() -> None:
    provider = KokoroTTSProvider(
        pipeline_loader=lambda **kwargs: pytest.fail("pipeline should not load")
    )

    with pytest.raises(TTSProviderError, match="language must be"):
        provider.synthesize("Hello", "fr")


def test_pipeline_is_loaded_once_per_language() -> None:
    pipeline = FakePipeline()
    loader_calls: list[str] = []

    def pipeline_loader(*, lang_code, **kwargs):
        loader_calls.append(lang_code)
        return pipeline

    provider = KokoroTTSProvider(pipeline_loader=pipeline_loader)
    provider.synthesize("Hello", "en")
    provider.synthesize("Hello again", "en")

    assert loader_calls == ["a"]


def test_pipeline_load_failure_is_wrapped_without_internal_details() -> None:
    def failing_loader(**kwargs):
        raise RuntimeError("private model path")

    provider = KokoroTTSProvider(pipeline_loader=failing_loader)

    with pytest.raises(TTSProviderError, match="model could not be loaded") as error:
        provider.synthesize("Hello", "en")

    assert "private model path" not in str(error.value)


def test_synthesis_failure_is_wrapped() -> None:
    class FailingPipeline:
        def __call__(self, text, voice):
            raise RuntimeError("private inference detail")

    provider = KokoroTTSProvider(pipeline_loader=lambda **kwargs: FailingPipeline())

    with pytest.raises(TTSProviderError, match="Text synthesis failed") as error:
        provider.synthesize("Hello", "en")

    assert "private inference detail" not in str(error.value)


def test_empty_provider_output_is_rejected() -> None:
    class EmptyPipeline:
        def __call__(self, text, voice):
            return iter(())

    provider = KokoroTTSProvider(pipeline_loader=lambda **kwargs: EmptyPipeline())

    with pytest.raises(TTSProviderError, match="returned no audio"):
        provider.synthesize("Hello", "en")
