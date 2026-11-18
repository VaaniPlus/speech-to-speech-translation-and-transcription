"""Lazy IndicTrans2 translation provider adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.providers.stage2_text_to_text_translation import (
    TranslationProviderError,
    TranslationResult,
)
from app.schemas.translation import (
    LANGUAGES_BY_DIRECTION,
    TranslationDirection,
)


@dataclass(frozen=True)
class TranslationModelConfig:
    """IndicTrans2 source and target language codes for one direction."""

    indic_source_code: str
    indic_target_code: str


TRANSLATION_MODEL_CONFIGS: dict[TranslationDirection, TranslationModelConfig] = {
    "en-to-hi": TranslationModelConfig("eng_Latn", "hin_Deva"),
    "hi-to-en": TranslationModelConfig("hin_Deva", "eng_Latn"),
}


class IndicTrans2TranslationProvider:
    """Translate English/Hindi with lazy-loaded IndicTrans2 checkpoints."""

    def __init__(
        self,
        en_hi_model_id: str = "ai4bharat/indictrans2-en-indic-dist-200M",
        hi_en_model_id: str = "ai4bharat/indictrans2-indic-en-dist-200M",
        device: str = "auto",
        cache_dir: str | Path | None = None,
        runtime_loader: Callable[..., tuple[Any, Any, Any, Any]] | None = None,
    ) -> None:
        self.model_ids: dict[TranslationDirection, str] = {
            "en-to-hi": en_hi_model_id,
            "hi-to-en": hi_en_model_id,
        }
        self.device = device
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._runtime_loader = runtime_loader
        self._runtimes: dict[TranslationDirection, tuple[Any, Any, Any, Any]] = {}

    def _resolve_device(self, torch_module: Any) -> str:
        if self.device == "auto":
            return "cuda" if torch_module.cuda.is_available() else "cpu"
        if self.device == "cuda" and not torch_module.cuda.is_available():
            raise TranslationProviderError("CUDA was requested but is unavailable")
        return self.device

    def _load_runtime(
        self,
        direction: TranslationDirection,
        model_id: str,
    ) -> tuple[Any, Any, Any, Any]:
        if direction in self._runtimes:
            return self._runtimes[direction]

        try:
            if self._runtime_loader is not None:
                runtime = self._runtime_loader(
                    model_id,
                    device=self.device,
                    cache_dir=str(self.cache_dir) if self.cache_dir else None,
                )
            else:
                import torch
                from IndicTransToolkit.processor import IndicProcessor
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

                device = self._resolve_device(torch)
                dtype = torch.float16 if device == "cuda" else torch.float32
                tokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    cache_dir=str(self.cache_dir) if self.cache_dir else None,
                )
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    torch_dtype=dtype,
                    cache_dir=str(self.cache_dir) if self.cache_dir else None,
                ).to(device)
                processor = IndicProcessor(inference=True)
                runtime = (tokenizer, model, processor, torch)
                runtime = (runtime[0], runtime[1], runtime[2], (device, runtime[3]))
        except TranslationProviderError:
            raise
        except ImportError as error:
            raise TranslationProviderError(
                "IndicTrans2 dependencies are not installed; run "
                "`uv sync --project backend --extra ml`"
            ) from error
        except Exception as error:
            raise TranslationProviderError("The translation model could not be loaded") from error

        self._runtimes[direction] = runtime
        return runtime

    def translate(
        self,
        source_text: str,
        direction: TranslationDirection,
    ) -> TranslationResult:
        if direction not in TRANSLATION_MODEL_CONFIGS:
            raise TranslationProviderError("Unsupported translation direction")
        if not isinstance(source_text, str) or not source_text.strip():
            raise TranslationProviderError("Source text must not be empty")

        mapping = TRANSLATION_MODEL_CONFIGS[direction]
        model_id = self.model_ids[direction]

        try:
            runtime = self._load_runtime(direction, model_id)
            tokenizer, model, processor, runtime_metadata = runtime

            if isinstance(runtime_metadata, tuple):
                device, torch_module = runtime_metadata
            else:
                device = self._resolve_device(runtime_metadata)
                torch_module = runtime_metadata

            batch = processor.preprocess_batch(
                [source_text.strip()],
                src_lang=mapping.indic_source_code,
                tgt_lang=mapping.indic_target_code,
            )
            inputs = tokenizer(
                batch,
                truncation=True,
                padding="longest",
                return_tensors="pt",
                return_attention_mask=True,
            )
            if hasattr(inputs, "to"):
                inputs = inputs.to(device)

            with torch_module.no_grad():
                generated = model.generate(
                    **inputs,
                    use_cache=True,
                    min_length=0,
                    max_length=256,
                    num_beams=5,
                    num_return_sequences=1,
                )
            decoded = tokenizer.batch_decode(
                generated,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )
            translations = processor.postprocess_batch(
                decoded,
                lang=mapping.indic_target_code,
            )
        except TranslationProviderError:
            raise
        except Exception as error:
            raise TranslationProviderError("Translation inference failed") from error

        if not translations:
            raise TranslationProviderError("The translation provider returned no output")
        translated_text = str(translations[0]).strip()
        if not translated_text:
            raise TranslationProviderError("The translation provider returned empty output")

        source_language, target_language = LANGUAGES_BY_DIRECTION[direction]
        return TranslationResult(
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            metadata={
                "provider": "indictrans2",
                "model_id": model_id,
                "device": device,
            },
        )
