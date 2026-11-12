"""Typed application settings loaded from environment variables and .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
Device = Literal["auto", "cpu", "cuda"]
ComputeType = Literal["auto", "int8", "int8_float16", "int16", "float16", "float32"]
ProviderMode = Literal["mock", "real"]


class Settings(BaseSettings):
    """Runtime configuration for the local speech translation application."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: LogLevel = "INFO"

    stt_model_id: str = Field(default="Systran/faster-whisper-small", min_length=1)
    translation_en_hi_model_id: str = Field(
        default="ai4bharat/indictrans2-en-indic-dist-200M", min_length=1
    )
    translation_hi_en_model_id: str = Field(
        default="ai4bharat/indictrans2-indic-en-dist-200M", min_length=1
    )
    tts_en_model_id: str = Field(default="hexgrad/Kokoro-82M", min_length=1)
    tts_hi_model_id: str = Field(default="hexgrad/Kokoro-82M", min_length=1)
    model_cache_dir: Path = Path("models")
    device: Device = "auto"
    stt_compute_type: ComputeType = "auto"
    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    provider_timeout_seconds: float = Field(default=120.0, gt=0)
    provider_mode: ProviderMode = Field(
        default="mock",
        description="Development mode; real provider adapters are not loaded in mock mode.",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator(
        "host",
        "stt_model_id",
        "translation_en_hi_model_id",
        "translation_hi_en_model_id",
        "tts_en_model_id",
        "tts_hi_model_id",
    )
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


def load_settings() -> Settings:
    """Load settings and raise a concise, readable error for invalid values."""
    try:
        return Settings()
    except ValidationError as error:
        details = "\n".join(
            f"- {'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}"
            for issue in error.errors()
        )
        raise ValueError(f"Invalid application configuration:\n{details}") from error


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return load_settings()
