"""Rotating application logging for the Linux GUI."""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path


def log_path() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return root / "Amatsukaze" / "LinuxGUI" / "AmatsukazeLinuxGUI.log"


def configure_logging() -> logging.Logger:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("amatsukaze_linux_gui")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger

    handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger

