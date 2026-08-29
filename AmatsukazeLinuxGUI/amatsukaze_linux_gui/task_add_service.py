"""Validation and request construction for the queue-add screen."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Iterable, Optional

from .api_client import ApiClient, RequestCancelled
from .dto import AddQueueRequest, ProcMode, Target
from .path_service import PathCollection, collect_paths, validate_output_directory


class TaskAddError(ValueError):
    """A user-correctable queue-add validation error."""


@dataclass(frozen=True)
class PreparedTargets:
    paths: list[str]
    rejected: list[str]


@dataclass(frozen=True)
class TaskAddResult:
    response: object
    request: AddQueueRequest


def prepare_targets(values: Iterable[str]) -> PreparedTargets:
    collection: PathCollection = collect_paths(values)
    rejected = [f"{item.path}: {item.reason}" for item in collection.rejected]
    return PreparedTargets(paths=collection.accepted, rejected=rejected)


def build_add_queue_request(
    paths: Iterable[str],
    *,
    profile: str,
    output_dir: str,
    priority: int,
    mode: ProcMode,
    add_queue_bat: Optional[str] = None,
) -> AddQueueRequest:
    normalized_paths = [str(path) for path in paths if str(path).strip()]
    if not normalized_paths:
        raise TaskAddError("入力ファイルを1件以上追加してください")
    profile = (profile or "").strip()
    if not profile:
        raise TaskAddError("プロファイルを選択してください")
    try:
        priority = int(priority)
    except (TypeError, ValueError) as exc:
        raise TaskAddError("優先度が不正です") from exc
    if not 1 <= priority <= 5:
        raise TaskAddError("優先度は1～5で指定してください")
    if not isinstance(mode, ProcMode):
        try:
            mode = ProcMode(str(mode))
        except ValueError as exc:
            raise TaskAddError("処理モードが不正です") from exc
    output_path, output_error = validate_output_directory(output_dir)
    if output_error:
        raise TaskAddError(output_error)
    targets = [Target(path=path) for path in normalized_paths]
    parent = os.path.dirname(targets[0].path) or os.path.abspath(os.curdir)
    return AddQueueRequest(
        dir_path=parent,
        targets=targets,
        profile=profile,
        output_dir=output_path,
        priority=priority,
        mode=mode,
        add_queue_bat=(add_queue_bat or "").strip() or None,
    )


class TaskAddService:
    """Submit one multi-target request and expose the server cancel operation."""

    def __init__(self, api: ApiClient) -> None:
        self.api = api

    def build_request(
        self,
        paths: Iterable[str],
        *,
        profile: str,
        output_dir: str,
        priority: int,
        mode: ProcMode,
        add_queue_bat: Optional[str] = None,
    ) -> AddQueueRequest:
        prepared = prepare_targets(paths)
        if prepared.rejected:
            raise TaskAddError("入力に利用できない項目があります:\n" + "\n".join(prepared.rejected))
        return build_add_queue_request(
            prepared.paths,
            profile=profile,
            output_dir=output_dir,
            priority=priority,
            mode=mode,
            add_queue_bat=add_queue_bat,
        )

    def submit(
        self,
        request: AddQueueRequest,
        *,
        cancel_event: Optional[threading.Event] = None,
    ) -> TaskAddResult:
        if cancel_event is not None and cancel_event.is_set():
            raise RequestCancelled("キュー追加をキャンセルしました")
        response = self.api.add_queue(request, cancel_event=cancel_event)
        return TaskAddResult(response=response, request=request)

    def cancel_server_add(self) -> object:
        return self.api.cancel_add_queue()
