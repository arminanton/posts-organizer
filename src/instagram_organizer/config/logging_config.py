"""Logging bootstrap utilities."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from instagram_organizer.config.settings import LoggingSettings


def configure_logging(settings: LoggingSettings) -> logging.Logger:
    """Configure application logging.

    Args:
        settings: Logging configuration values.

    Returns:
        The package logger.
    """

    logger = logging.getLogger("instagram_organizer")
    logger.setLevel(getattr(logging, settings.level, logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    for filename, level in (
        (settings.app_log_file, logging.INFO),
        (settings.error_log_file, logging.ERROR),
    ):
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger
