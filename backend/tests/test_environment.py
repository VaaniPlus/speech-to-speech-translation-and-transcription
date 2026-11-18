"""Checks for the lightweight development environment."""

import sys

import fastapi
import httpx
import pydantic
import pytest
import uvicorn

from app.core.config import Settings, get_settings


def test_supported_python_and_core_dependencies() -> None:
    assert sys.version_info[:2] == (3, 11)
    assert fastapi.__version__
    assert uvicorn.__version__
    assert pydantic.__version__
    assert pytest.__version__
    assert httpx.__version__


def test_settings_have_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.log_level == "INFO"
    assert settings.device == "auto"
    assert settings.max_upload_size_bytes == 25 * 1024 * 1024
    assert settings.provider_timeout_seconds == 120.0
    assert settings.model_cache_dir.name == "models"


def test_settings_read_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("DEVICE", "cpu")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "1048576")
    monkeypatch.setenv("PROVIDER_TIMEOUT_SECONDS", "45")

    settings = Settings(_env_file=None)

    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.log_level == "DEBUG"
    assert settings.device == "cpu"
    assert settings.max_upload_size_bytes == 1048576
    assert settings.provider_timeout_seconds == 45.0


def test_settings_read_dotenv_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("PORT=8123\nMODEL_CACHE_DIR=local-models\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.port == 8123
    assert settings.model_cache_dir.as_posix() == "local-models"


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("PORT", "70000", "port"),
        ("DEVICE", "tpu", "device"),
        ("MAX_UPLOAD_SIZE_BYTES", "0", "max_upload_size_bytes"),
        ("PROVIDER_TIMEOUT_SECONDS", "0", "provider_timeout_seconds"),
        ("LOG_LEVEL", "TRACE", "log_level"),
    ],
)
def test_invalid_environment_is_reported_readably(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str, expected: str
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match="Invalid application configuration") as error:
        get_settings()

    assert expected in str(error.value)
    get_settings.cache_clear()
