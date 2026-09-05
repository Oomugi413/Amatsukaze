"""REST DTOs used by the Linux GUI.

The C# shared DTOs are the contract of record.  This module deliberately keeps
the Python representation small and serializes the same camelCase JSON names
that ASP.NET's web defaults use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Optional


INPUT_EXTENSIONS = (".ts", ".m2t")
DEFAULT_REST_PORT = 32769
PRIORITIES = (1, 2, 3, 4, 5)


class ProcMode(str, Enum):
    """Values of Amatsukaze.Shared.ProcMode used by the queue add screen."""

    BATCH = "Batch"
    TEST = "Test"
    DRCS_CHECK = "DrcsCheck"
    CM_CHECK = "CMCheck"


PROC_MODE_LABELS = {
    ProcMode.BATCH: "通常",
    ProcMode.TEST: "テスト",
    ProcMode.DRCS_CHECK: "DRCSチェック",
    ProcMode.CM_CHECK: "CM解析",
}


def _case_insensitive_get(value: Any, name: str, default: Any = None) -> Any:
    """Read a JSON property while tolerating C# and hand-written casing."""

    if not isinstance(value, Mapping):
        return default
    wanted = name.casefold()
    for key, item in value.items():
        if str(key).casefold() == wanted:
            return item
    return default


def profile_name(value: Any) -> Optional[str]:
    """Extract a profile name from a JSON object returned by /api/profiles."""

    name = _case_insensitive_get(value, "name")
    if name is None:
        return None
    text = str(name).strip()
    return text or None


def profile_names(values: Iterable[Any]) -> list[str]:
    """Return unique, non-empty profile names while retaining server order."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        name = profile_name(value)
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def profile_option_pre_bat_files(value: Any) -> list[str]:
    """Extract the add-queue batch list from ProfileOptions."""

    values = _case_insensitive_get(value, "preBatFiles", [])
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item).strip()]


def ui_state_value(value: Any, name: str) -> Optional[str]:
    """Extract a nullable string from the server UI state."""

    item = _case_insensitive_get(value, name)
    if item is None:
        return None
    text = str(item).strip()
    return text or None


@dataclass(frozen=True)
class Target:
    path: str
    file_hash: Optional[list[int]] = None

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {"path": self.path}
        if self.file_hash is not None:
            result["hash"] = self.file_hash
        return result


@dataclass(frozen=True)
class OutputInfo:
    dst_path: str
    profile: str
    priority: int

    def to_json(self) -> dict[str, Any]:
        return {
            "dstPath": self.dst_path,
            "profile": self.profile,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class AddQueueRequest:
    """Small Python equivalent of Amatsukaze.Shared.AddQueueRequest."""

    dir_path: str
    targets: list[Target]
    profile: str
    output_dir: str
    priority: int
    mode: ProcMode
    add_queue_bat: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    request_id: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "dirPath": self.dir_path,
            "targets": [target.to_json() for target in self.targets],
            "mode": self.mode.value,
            "outputs": [
                OutputInfo(
                    dst_path=self.output_dir,
                    profile=self.profile,
                    priority=self.priority,
                ).to_json()
            ],
            "addQueueBat": self.add_queue_bat,
            "tags": list(self.tags),
        }
        if self.request_id:
            result["requestId"] = self.request_id
        return result


@dataclass(frozen=True)
class UiState:
    last_used_profile: Optional[str] = None
    last_output_path: Optional[str] = None
    last_add_queue_bat: Optional[str] = None

    @classmethod
    def from_json(cls, value: Any) -> "UiState":
        return cls(
            last_used_profile=ui_state_value(value, "lastUsedProfile"),
            last_output_path=ui_state_value(value, "lastOutputPath"),
            last_add_queue_bat=ui_state_value(value, "lastAddQueueBat"),
        )

