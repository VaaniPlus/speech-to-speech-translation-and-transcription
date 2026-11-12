"""Structured application logging and request correlation context."""

from contextvars import ContextVar, Token
from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any

request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

_STRUCTURED_FIELDS = (
    "event",
    "request_id",
    "method",
    "path",
    "status_code",
    "stage",
    "outcome",
    "duration_ms",
    "timeout_seconds",
    "error_code",
    "error_type",
    "direction",
    "requested_language",
    "detected_language",
)
_ALLOWED_EVENT_FIELDS = frozenset(_STRUCTURED_FIELDS) - {
    "event",
    "request_id",
}

_record_factory_configured = False


class JsonLogFormatter(logging.Formatter):
    """Format log records as one privacy-safe JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        for field in _STRUCTURED_FIELDS:
            if field == "event":
                continue
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        return json.dumps(entry, ensure_ascii=False, separators=(",", ":"))


def set_request_id(request_id: str) -> Token[str | None]:
    """Set the current request ID and return its reset token."""
    return request_id_context.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the request context that was active before this request."""
    request_id_context.reset(token)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    request_id: str | None = None,
    **fields: str | int | float,
) -> None:
    """Emit a structured event without accepting arbitrary payload fields."""
    unknown_fields = set(fields) - _ALLOWED_EVENT_FIELDS
    if unknown_fields:
        raise ValueError(
            f"Unsupported structured log fields: {', '.join(sorted(unknown_fields))}"
        )
    if request_id is None:
        logger.log(level, event, extra={"event": event, **fields})
        return

    token = set_request_id(request_id)
    try:
        logger.log(level, event, extra={"event": event, **fields})
    finally:
        reset_request_id(token)


def configure_logging(level: str) -> None:
    """Configure JSON logs on stderr and attach request IDs to log records."""
    global _record_factory_configured

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler(sys.stderr))

    for handler in root_logger.handlers:
        handler.setFormatter(JsonLogFormatter())

    if not _record_factory_configured:
        previous_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = previous_factory(*args, **kwargs)
            record.request_id = request_id_context.get()
            return record

        logging.setLogRecordFactory(record_factory)
        _record_factory_configured = True
