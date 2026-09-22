"""Minimal standard-library REST client for AmatsukazeServer."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .dto import AddQueueRequest


class ApiError(RuntimeError):
    """An HTTP, transport, or JSON error returned by the REST client."""

    def __init__(self, message: str, *, status: int = 0, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class RequestCancelled(ApiError):
    """Raised when a caller cancels before an HTTP request is started."""


@dataclass(frozen=True)
class ApiResponse:
    status: int
    data: Any


def is_loopback_url(value: str) -> bool:
    """Return whether a URL is an allowed local REST endpoint."""

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    if parsed.path not in ("", "/"):
        return False
    hostname = (parsed.hostname or "").casefold()
    return hostname in {"127.0.0.1", "localhost", "::1"}


def make_loopback_url(port: int) -> str:
    if not 1 <= int(port) <= 65535:
        raise ValueError("ポート番号は1～65535で指定してください")
    return f"http://127.0.0.1:{int(port)}"


def extract_error_message(body: str, fallback: str = "REST APIエラー") -> str:
    """Extract the useful part of the server's JSON or text error body."""

    text = (body or "").strip()
    if not text:
        return fallback
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return text
    if isinstance(value, dict):
        for key in ("error", "message", "detail", "title"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        errors = value.get("errors")
        if isinstance(errors, dict):
            values: list[str] = []
            for item in errors.values():
                if isinstance(item, list):
                    values.extend(str(v) for v in item if str(v).strip())
                elif item:
                    values.append(str(item))
            if values:
                return "; ".join(values)
    return text


class ApiClient:
    """Thread-safe-by-usage REST client.

    Each operation creates its own urllib request.  The GUI invokes operations
    from worker threads and never touches GTK from this class.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 15.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self._opener = opener
        self.timeout = float(timeout)
        self.base_url = ""
        self.set_base_url(base_url)

    def set_base_url(self, base_url: str) -> None:
        value = (base_url or "").strip().rstrip("/")
        if not is_loopback_url(value):
            raise ValueError("接続先はlocalhost、127.0.0.1、::1のいずれかにしてください")
        self.base_url = value

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    @staticmethod
    def _check_cancel(cancel_event: Optional[threading.Event]) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise RequestCancelled("RESTリクエストをキャンセルしました")

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Any = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> ApiResponse:
        self._check_cancel(cancel_event)
        headers = {"Accept": "application/json"}
        data: Optional[bytes] = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = Request(self._url(path), data=data, headers=headers, method=method)
        try:
            with self._opener(request, timeout=self.timeout) as response:
                body = response.read()
                status_value = getattr(response, "status", None)
                status = int(status_value if status_value is not None else response.getcode())
        except HTTPError as exc:
            body_bytes = exc.read()
            body_text = body_bytes.decode("utf-8", errors="replace")
            message = extract_error_message(body_text, f"HTTP {exc.code}")
            raise ApiError(message, status=int(exc.code), body=body_text) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ApiError(f"RESTサーバーへ接続できません: {exc}") from exc
        self._check_cancel(cancel_event)
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
        if not 200 <= status < 300:
            raise ApiError(
                extract_error_message(text, f"HTTP {status}"),
                status=status,
                body=text,
            )
        if not text.strip():
            return ApiResponse(status=status, data={})
        try:
            value = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise ApiError("REST APIのJSON応答を解釈できません", status=status, body=text) from exc
        return ApiResponse(status=status, data=value)

    def get_json(self, path: str, *, cancel_event: Optional[threading.Event] = None) -> Any:
        return self._request("GET", path, cancel_event=cancel_event).data

    def post_json(self, path: str, payload: Any, *, cancel_event: Optional[threading.Event] = None) -> Any:
        return self._request("POST", path, payload=payload, cancel_event=cancel_event).data

    def health(self, *, cancel_event: Optional[threading.Event] = None) -> Any:
        return self.get_json("/api/health", cancel_event=cancel_event)

    def get_profiles(self, *, cancel_event: Optional[threading.Event] = None) -> list[Any]:
        value = self.get_json("/api/profiles", cancel_event=cancel_event)
        if not isinstance(value, list):
            raise ApiError("プロファイル一覧の形式が不正です")
        return value

    def get_profile_options(self, *, cancel_event: Optional[threading.Event] = None) -> Any:
        return self.get_json("/api/profile-options", cancel_event=cancel_event)

    def get_ui_state(self, *, cancel_event: Optional[threading.Event] = None) -> Any:
        return self.get_json("/api/ui-state", cancel_event=cancel_event)

    def get_info_summary(self, *, cancel_event: Optional[threading.Event] = None) -> Any:
        return self.get_json("/api/info/summary", cancel_event=cancel_event)

    def add_queue(
        self,
        request: AddQueueRequest,
        *,
        cancel_event: Optional[threading.Event] = None,
    ) -> Any:
        return self.post_json("/api/queue/add", request.to_json(), cancel_event=cancel_event)

    def cancel_add_queue(self) -> Any:
        # 現行APIはリクエストIDを受け付けず、サーバーの追加処理全体を停止する。
        return self.post_json("/api/queue/cancel-add", {})
