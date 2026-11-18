"""Unit tests for the optional IndicTrans2 provider adapter."""

from contextlib import nullcontext

import pytest

from app.providers.stage2_text_to_text_translation_indictrans2 import IndicTrans2TranslationProvider
from app.providers.stage2_text_to_text_translation import TranslationProviderError
from app.schemas.translation import LANGUAGES_BY_DIRECTION


class FakeCuda:
    @staticmethod
    def is_available() -> bool:
        return False


class FakeTorch:
    cuda = FakeCuda()

    @staticmethod
    def no_grad():
        return nullcontext()


class FakeProcessor:
    def __init__(self) -> None:
        self.preprocess_calls: list[tuple[list[str], str, str]] = []
        self.output: str | None = "translated output"

    def preprocess_batch(self, texts, src_lang, tgt_lang):
        self.preprocess_calls.append((texts, src_lang, tgt_lang))
        return texts

    def postprocess_batch(self, texts, lang):
        assert lang
        return [self.output] if self.output is not None else []


class FakeTokenizer:
    def __call__(self, batch, **kwargs):
        return dict(input_ids=[1])

    def batch_decode(self, generated, **kwargs):
        return ["decoded output"]


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return [1]


@pytest.fixture
def fake_runtime():
    processor = FakeProcessor()
    tokenizer = FakeTokenizer()
    model = FakeModel()
    calls: list[tuple[str, dict[str, object]]] = []

    def runtime_loader(model_id, **kwargs):
        calls.append((model_id, kwargs))
        return tokenizer, model, processor, FakeTorch()

    provider = IndicTrans2TranslationProvider(
        device="cpu",
        runtime_loader=runtime_loader,
    )
    return provider, processor, model, calls


@pytest.mark.parametrize(
    ("direction", "source", "source_code", "target_code", "model_id"),
    [
        (
            "en-to-hi",
            "Hello, how are you?",
            "eng_Latn",
            "hin_Deva",
            "ai4bharat/indictrans2-en-indic-dist-200M",
        ),
        (
            "hi-to-en",
            "नमस्ते, आप कैसे हैं?",
            "hin_Deva",
            "eng_Latn",
            "ai4bharat/indictrans2-indic-en-dist-200M",
        ),
    ],
)
def test_supports_both_directions_with_centralized_mapping(
    fake_runtime,
    direction,
    source,
    source_code,
    target_code,
    model_id,
) -> None:
    provider, processor, model, calls = fake_runtime

    result = provider.translate(source, direction)

    assert result.translated_text == "translated output"
    source_language, target_language = LANGUAGES_BY_DIRECTION[direction]
    assert result.source_language == source_language
    assert result.target_language == target_language
    assert processor.preprocess_calls == [( [source.strip()], source_code, target_code )]
    assert calls[0][0] == model_id
    assert calls[0][1]["device"] == "cpu"
    assert model.calls


def test_reuses_lazy_runtime_per_direction(fake_runtime) -> None:
    provider, _, _, calls = fake_runtime

    provider.translate("Hello", "en-to-hi")
    provider.translate("Hello again", "en-to-hi")

    assert len(calls) == 1


def test_empty_source_is_rejected(fake_runtime) -> None:
    provider, _, _, _ = fake_runtime

    with pytest.raises(TranslationProviderError, match="Source text"):
        provider.translate("   ", "en-to-hi")


def test_empty_model_output_is_rejected(fake_runtime) -> None:
    provider, processor, _, _ = fake_runtime
    processor.output = "  "

    with pytest.raises(TranslationProviderError, match="empty output"):
        provider.translate("Hello", "en-to-hi")


def test_model_exception_is_wrapped(fake_runtime) -> None:
    provider, _, _, _ = fake_runtime

    def failing_loader(*args, **kwargs):
        raise RuntimeError("private loader detail")

    provider._runtime_loader = failing_loader

    with pytest.raises(TranslationProviderError, match="could not be loaded") as error:
        provider.translate("Hello", "en-to-hi")

    assert "private loader detail" not in str(error.value)


def test_load_failure_message_is_safe(fake_runtime) -> None:
    provider, _, _, _ = fake_runtime

    def failing_loader(*args, **kwargs):
        raise ImportError("missing optional package")

    provider._runtime_loader = failing_loader

    with pytest.raises(TranslationProviderError, match="not installed"):
        provider.translate("Hello", "hi-to-en")
