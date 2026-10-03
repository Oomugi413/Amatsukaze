"""XDG-compliant local settings for the Linux GUI."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .dto import DEFAULT_REST_PORT


@dataclass
class GuiSettings:
    rest_port: int = DEFAULT_REST_PORT
    window_width: int = 960
    window_height: int = 720

    @classmethod
    def from_json(cls, value: Any) -> "GuiSettings":
        if not isinstance(value, dict):
            return cls()

        def positive_int(name: str, fallback: int, minimum: int, maximum: int) -> int:
            item = value.get(name, fallback)
            try:
                number = int(item)
            except (TypeError, ValueError):
                return fallback
            return number if minimum <= number <= maximum else fallback

        return cls(
            rest_port=positive_int("rest_port", DEFAULT_REST_PORT, 1, 65535),
            window_width=positive_int("window_width", 960, 480, 10000),
            window_height=positive_int("window_height", 720, 360, 10000),
        )

    def to_json(self) -> dict[str, int]:
        return {
            "rest_port": int(self.rest_port),
            "window_width": int(self.window_width),
            "window_height": int(self.window_height),
        }


def _config_home() -> Path:
    value = os.environ.get("XDG_CONFIG_HOME")
    return Path(value).expanduser() if value else Path.home() / ".config"


def settings_path() -> Path:
    return _config_home() / "Amatsukaze" / "LinuxGUI.json"


def load_settings(path: Path | None = None) -> GuiSettings:
    target = path or settings_path()
    try:
        with target.open("r", encoding="utf-8") as stream:
            return GuiSettings.from_json(json.load(stream))
    except (OSError, ValueError, TypeError):
        return GuiSettings()


def save_settings(settings: GuiSettings, path: Path | None = None) -> None:
    """Atomically write settings and keep the file private to the user."""

    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(settings.to_json(), stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise

