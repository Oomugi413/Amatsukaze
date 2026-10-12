"""Local path normalization and the Linux GUI input policy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .dto import INPUT_EXTENSIONS


@dataclass(frozen=True)
class RejectedPath:
    path: str
    reason: str


@dataclass(frozen=True)
class PathCollection:
    accepted: list[str]
    rejected: list[RejectedPath]


def normalize_path(value: str) -> str:
    """Normalize without resolving symlinks, as required by the design."""

    text = os.path.expanduser((value or "").strip())
    if not text:
        return ""
    return os.path.normpath(os.path.abspath(text))


def has_allowed_extension(path: str) -> bool:
    suffix = Path(path).suffix.casefold()
    return suffix in {extension.casefold() for extension in INPUT_EXTENSIONS}


def _append_file(
    path: str,
    accepted: list[str],
    rejected: list[RejectedPath],
    seen: set[str],
) -> None:
    normalized = normalize_path(path)
    if not normalized:
        rejected.append(RejectedPath(path, "空のパスです"))
        return
    if normalized in seen:
        rejected.append(RejectedPath(normalized, "重複したパスです"))
        return
    if not os.path.exists(normalized):
        rejected.append(RejectedPath(normalized, "ファイルが存在しません"))
        return
    if not os.path.isfile(normalized):
        rejected.append(RejectedPath(normalized, "通常ファイルではありません"))
        return
    if not has_allowed_extension(normalized):
        rejected.append(RejectedPath(normalized, "対象拡張子ではありません（.ts / .m2t のみ）"))
        return
    seen.add(normalized)
    accepted.append(normalized)


def collect_paths(values: Iterable[str]) -> PathCollection:
    """Expand files/directories once and return accepted/rejected entries.

    Directory expansion is intentionally non-recursive.  Directory entries are
    sorted by their normalized path so a drop produces a stable request and a
    repeatable test result.  Symlinks are not resolved; ``isfile``/``isdir``
    only checks whether the current process can access their target.
    """

    accepted: list[str] = []
    rejected: list[RejectedPath] = []
    seen: set[str] = set()
    for raw in values:
        normalized = normalize_path(raw)
        if not normalized:
            rejected.append(RejectedPath(str(raw), "空のパスです"))
            continue
        if os.path.isdir(normalized):
            children: list[str] = []
            try:
                with os.scandir(normalized) as entries:
                    children = sorted(
                        (entry.path for entry in entries if entry.is_file(follow_symlinks=True)),
                        key=lambda item: normalize_path(item),
                    )
            except OSError as exc:
                rejected.append(RejectedPath(normalized, f"ディレクトリを読み取れません: {exc}"))
                continue
            before = len(accepted)
            for child in children:
                _append_file(child, accepted, rejected, seen)
            if len(accepted) == before:
                rejected.append(RejectedPath(normalized, "対象拡張子のファイルがありません"))
            continue
        _append_file(normalized, accepted, rejected, seen)
    return PathCollection(accepted=accepted, rejected=rejected)


def validate_output_directory(value: str) -> tuple[str, str | None]:
    """Normalize an output path without requiring it to already exist.

    The server only requires a non-empty destination.  Existing paths must be
    directories; a not-yet-created destination remains valid so the server can
    apply its normal output-directory behavior.
    """

    normalized = normalize_path(value)
    if not normalized:
        return "", "出力先ディレクトリを指定してください"
    if os.path.exists(normalized) and not os.path.isdir(normalized):
        return normalized, "出力先がディレクトリではありません"
    return normalized, None

