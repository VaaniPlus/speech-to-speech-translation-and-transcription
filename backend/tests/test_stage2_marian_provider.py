"""Tests for the MarianMT translation provider."""

import sys
from types import ModuleType
from typing import Any

import pytest

from app.providers.stage2_text_to_text_translation_marian import (
    MarianTranslationProvider,
)


def test_model_load_disables_low_memory_meta_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_calls: list[tuple[str, str | None]] = []
    model_options: dict[str, Any] = {}

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, model_id: str, cache_dir: str | None = None):
            load_calls.append((model_id, cache_dir))
            return cls()

    class FakeModel:
        @classmethod
        def from_pretrained(
            cls,
            model_id: str,
            cache_dir: str | None = None,
            **options: Any,
        ):
            load_calls.append((model_id, cache_dir))
            model_options.update(options)
            return cls()

        def eval(self) -> None:
            pass

    transformers = ModuleType("transformers")
    setattr(transformers, "MarianMTModel", FakeModel)
    setattr(transformers, "MarianTokenizer", FakeTokenizer)
    monkeypatch.setitem(sys.modules, "transformers", transformers)

    provider = MarianTranslationProvider()
    provider._load_runtime("en-to-hi")

    assert load_calls == [
        ("Helsinki-NLP/opus-mt-en-hi", None),
        ("Helsinki-NLP/opus-mt-en-hi", None),
    ]
    assert model_options["low_cpu_mem_usage"] is False
