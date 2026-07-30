"""Structured, human-friendly logging setup.

We use the stdlib `logging` module (no extra dependency) configured once at
startup via `setup_logging()`. In `local`/`dev` we emit compact console lines;
in production you'd typically switch the formatter to JSON so a log aggregator
(Datadog, Loki, CloudWatch) can parse fields. Keeping this behind one function
means the rest of the codebase just calls `get_logger(__name__)`.
"""

from __future__ import annotations

import logging
from logging.config import dictConfig

from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    level = settings.LOG_LEVEL.upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "level": level,
                }
            },
            # Tame noisy libraries; let our app logs flow at the configured level.
            "loggers": {
                "uvicorn.access": {"level": "WARNING"},
                "app": {"level": level, "handlers": ["console"], "propagate": False},
            },
            "root": {"level": level, "handlers": ["console"]},
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (e.g. `get_logger(__name__)`)."""
    return logging.getLogger(name if name.startswith("app") else f"app.{name}")
