"""MarianMT translation provider using the standard Transformers API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.providers.stage2_text_to_text_translation import (
    TranslationProviderError,
    TranslationResult,
)
from app.schemas.translation import LANGUAGES_BY_DIRECTION, TranslationDirection

logger = logging.getLogger(__name__)

# Helsinki-NLP MarianMT models for English <-> Hindi
MARIAN_MODEL_IDS: dict[TranslationDirection, str] = {
    "en-to-hi": "Helsinki-NLP/opus-mt-en-hi",
    "hi-to-en": "Helsinki-NLP/opus-mt-hi-en",
}


class MarianTranslationProvider:
    """Translate English/Hindi with lazy-loaded Helsinki-NLP MarianMT checkpoints.

    Requires only ``transformers`` and ``sentencepiece`` — no C++ compiler needed.
    Models (~300 MB each) are downloaded from Hugging Face on first use.
    """

    def __init__(
        self,
        device: str = "cpu",
        cache_dir: str | Path | None = None,
    ) -> None:
        self.device = device
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._runtimes: dict[TranslationDirection, tuple[Any, Any]] = {}

    def _load_runtime(self, direction: TranslationDirection) -> tuple[Any, Any]:
        if direction in self._runtimes:
            return self._runtimes[direction]

        model_id = MARIAN_MODEL_IDS.get(direction)
        if model_id is None:
            raise TranslationProviderError("Unsupported translation direction")

        try:
            from transformers import MarianMTModel, MarianTokenizer

            cache = str(self.cache_dir) if self.cache_dir else None
            tokenizer = MarianTokenizer.from_pretrained(model_id, cache_dir=cache)
            model = MarianMTModel.from_pretrained(
                model_id,
                cache_dir=cache,
                low_cpu_mem_usage=False,
            )
            model.eval()
        except ImportError as error:
            logger.exception("MarianMT import error: %s", error)
            raise TranslationProviderError(
                "MarianMT dependencies are not installed; run: "
                "pip install transformers sentencepiece"
            ) from error
        except Exception as error:
            logger.exception("MarianMT model load error: %s", error)
            raise TranslationProviderError(
                f"The MarianMT translation model could not be loaded: {error}"
            ) from error

        self._runtimes[direction] = (tokenizer, model)
        return tokenizer, model

    def translate(
        self,
        source_text: str,
        direction: TranslationDirection,
    ) -> TranslationResult:
        if direction not in MARIAN_MODEL_IDS:
            raise TranslationProviderError("Unsupported translation direction")
        if not isinstance(source_text, str) or not source_text.strip():
            raise TranslationProviderError("Source text must not be empty")

        try:
            import torch

            tokenizer, model = self._load_runtime(direction)
            inputs = tokenizer(
                [source_text.strip()],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )
            with torch.no_grad():
                translated_tokens = model.generate(**inputs)
            translated_text = tokenizer.batch_decode(
                translated_tokens, skip_special_tokens=True
            )[0].strip()
        except TranslationProviderError:
            raise
        except Exception as error:
            logger.exception("MarianMT translation inference failed: %s", error)
            raise TranslationProviderError(f"MarianMT translation inference failed: {error}") from error

        if not translated_text:
            raise TranslationProviderError("The translation provider returned empty output")

        source_language, target_language = LANGUAGES_BY_DIRECTION[direction]
        return TranslationResult(
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            metadata={
                "provider": "marian_mt",
                "model_id": MARIAN_MODEL_IDS[direction],
                "device": self.device,
            },
        )

