"""
Structured JSON logging.

Every log line is a machine-parseable JSON object containing:
  - timestamp, level, logger name, message
  - Any extra keyword arguments passed to logger.info("event", key=value)

This makes logs searchable in production (ELK, Datadog, CloudWatch, etc.)
and ensures session IDs are always attached for traceability.
"""
import sys
import logging
from pythonjsonlogger import json as json_logger


class _KwargsAdapter(logging.LoggerAdapter):
    """
    Custom adapter that lets you pass keyword arguments directly to log calls:

        logger.info("event_name", session_id="abc", key="value")

    Internally it funnels them into `extra`, which the JsonFormatter then
    includes in the JSON output.  This avoids the standard-library error:
        "Unexpected keyword argument 'session_id' in function Logger.info"
    """

    def process(self, msg, kwargs):
        # Move any non-standard kwargs into `extra` so JsonFormatter sees them
        extra = self.extra.copy() if self.extra else {}
        # Pop out the standard logging kwargs
        exc_info = kwargs.pop("exc_info", None)
        stack_info = kwargs.pop("stack_info", False)
        stacklevel = kwargs.pop("stacklevel", 1)
        # Everything remaining is a structured field
        extra.update(kwargs)
        kwargs = {
            "extra": extra,
            "exc_info": exc_info,
            "stack_info": stack_info,
            "stacklevel": stacklevel,
        }
        return msg, kwargs


def get_logger(name: str) -> _KwargsAdapter:
    """
    Return a structured JSON logger that supports keyword arguments.

    Usage:
        from core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("event_name", session_id="abc", key="value")
    """
    base_logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if called multiple times
    if not base_logger.handlers:
        base_logger.setLevel(logging.DEBUG)
        base_logger.propagate = False

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        formatter = json_logger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        )
        handler.setFormatter(formatter)
        base_logger.addHandler(handler)

    return _KwargsAdapter(base_logger, {})
