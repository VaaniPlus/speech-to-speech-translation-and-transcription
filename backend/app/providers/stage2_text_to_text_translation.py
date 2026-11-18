"""Translation provider interface and expected provider errors."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.schemas.translation import LanguageCode, TranslationDirection


@dataclass(frozen=True)
class TranslationResult:
    """A translated string and optional provider language metadata."""

    translated_text: str
    source_language: LanguageCode | str | None = None
    target_language: LanguageCode | str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Compatibility alias for the translated text."""
        return self.translated_text


class TranslationProviderError(Exception):
    """Expected failure raised by a translation provider."""


@runtime_checkable
class TranslationProvider(Protocol):
    """Translate source text in one of the supported directions."""

    def translate(
        self,
        source_text: str,
        direction: TranslationDirection,
    ) -> str | TranslationResult:
        """Return translated text/result or raise ``TranslationProviderError``."""
