"""Main GTK 4 window for adding Amatsukaze tasks."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

from .api_client import ApiClient, ApiError, RequestCancelled, make_loopback_url
from .dto import (
    PRIORITIES,
    PROC_MODE_LABELS,
    ProcMode,
    UiState,
    profile_names,
    profile_option_pre_bat_files,
)
from .path_service import PathCollection, RejectedPath, collect_paths
from .settings_service import GuiSettings, save_settings
from .task_add_service import TaskAddError, TaskAddService


class MainWindow(Gtk.ApplicationWindow):
    """Single-window task-add client; all blocking work runs outside GTK."""

    def __init__(
        self,
        application: Gtk.Application,
        *,
        settings: GuiSettings,
        api: ApiClient,
        logger: logging.Logger,
    ) -> None:
        super().__init__(application=application)
        self.settings = settings
        self.api = api
        self.task_service = TaskAddService(api)
        self.logger = logger
        self.set_title("Amatsukaze Linux GUI")
        self.set_default_size(settings.window_width, settings.window_height)
        self.connect("close-request", self._on_close_request)

        self._input_paths: list[str] = []
        self._input_rejections: list[RejectedPath] = []
        self._adding = False
        self._cancel_event: Optional[threading.Event] = None
        self._close_dialog_open = False
        self._allow_close = False
        self._load_generation = 0
        self._file_dialog: Optional[Gtk.FileDialog] = None
        self._profiles: list[str] = []
        self._batch_files: list[str] = []
        self._ui_state = UiState()

        self._build_ui()
        self._set_connection_status("接続確認中", False)
        self._start_server_load()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.set_child(root)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(header)
        title = Gtk.Label(label="Amatsukaze Linux GUI")
        title.set_xalign(0)
        title.add_css_class("title-3")
        header.append(title)
        self.connection_label = Gtk.Label(label="未接続")
        self.connection_label.set_hexpand(True)
        self.connection_label.set_xalign(1)
        header.append(self.connection_label)
        connection_button = Gtk.Button(label="接続設定")
        connection_button.connect("clicked", self._show_connection_dialog)
        header.append(connection_button)
        reconnect_button = Gtk.Button(label="再接続")
        reconnect_button.connect("clicked", lambda _button: self._start_server_load())
        header.append(reconnect_button)

        self.error_label = Gtk.Label()
        self.error_label.set_xalign(0)
        self.error_label.set_wrap(True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        root.append(self.error_label)

        drop_frame = Gtk.Frame(label="入力ファイル（.ts / .m2t）")
        drop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        drop_box.set_margin_top(12)
        drop_box.set_margin_bottom(12)
        drop_box.set_margin_start(12)
        drop_box.set_margin_end(12)
        drop_label = Gtk.Label(label="ここにTSファイルまたはフォルダーをドロップ")
        drop_label.set_xalign(0.5)
        drop_label.set_vexpand(True)
        drop_box.append(drop_label)
        drop_frame.set_child(drop_box)
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_drop)
        drop_frame.add_controller(drop_target)
        root.append(drop_frame)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        root.append(action_row)
        choose_files = Gtk.Button(label="ファイルを選択")
        choose_files.connect("clicked", self._choose_files)
        action_row.append(choose_files)
        choose_folder = Gtk.Button(label="フォルダーを選択")
        choose_folder.connect("clicked", self._choose_folder)
        action_row.append(choose_folder)
        add_path = Gtk.Button(label="パスを追加")
        add_path.connect("clicked", self._show_add_path_dialog)
        action_row.append(add_path)
        clear_paths = Gtk.Button(label="全消去")
        clear_paths.connect("clicked", self._clear_paths)
        action_row.append(clear_paths)

        list_frame = Gtk.Frame(label="追加対象")
        list_scroller = Gtk.ScrolledWindow()
        list_scroller.set_min_content_height(150)
        list_scroller.set_vexpand(True)
        self.input_list = Gtk.ListBox()
        self.input_list.set_selection_mode(Gtk.SelectionMode.NONE)
        list_scroller.set_child(self.input_list)
        list_frame.set_child(list_scroller)
        root.append(list_frame)

        form = Gtk.Grid(column_spacing=8, row_spacing=8)
        form.set_margin_top(4)
        form.set_margin_bottom(4)
        form.set_column_homogeneous(False)
        root.append(form)

        self.profile_combo = Gtk.ComboBoxText()
        self._append_form_row(form, 0, "プロファイル", self.profile_combo)

        output_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.output_entry = Gtk.Entry()
        self.output_entry.set_hexpand(True)
        self.output_entry.set_placeholder_text("出力先ディレクトリ")
        output_box.append(self.output_entry)
        output_button = Gtk.Button(label="フォルダー選択")
        output_button.connect("clicked", self._choose_output_folder)
        output_box.append(output_button)
        self._append_form_row(form, 1, "出力先", output_box)

        self.priority_combo = Gtk.ComboBoxText()
        for priority in PRIORITIES:
            self.priority_combo.append(str(priority), str(priority))
        self.priority_combo.set_active_id("3")
        self._append_form_row(form, 2, "優先度", self.priority_combo)

        self.batch_combo = Gtk.ComboBoxText()
        self.batch_combo.append("", "（なし）")
        self._append_form_row(form, 3, "追加時バッチ", self.batch_combo)

        self.mode_combo = Gtk.ComboBoxText()
        for mode in ProcMode:
            self.mode_combo.append(mode.value, PROC_MODE_LABELS[mode])
        self.mode_combo.set_active_id(ProcMode.BATCH.value)
        self._append_form_row(form, 4, "処理モード", self.mode_combo)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(bottom)
        self.add_button = Gtk.Button(label="キューに追加")
        self.add_button.add_css_class("suggested-action")
        self.add_button.connect("clicked", self._submit)
        bottom.append(self.add_button)
        self.cancel_button = Gtk.Button(label="以降の追加を停止")
        self.cancel_button.set_sensitive(False)
        self.cancel_button.connect("clicked", self._cancel_add)
        bottom.append(self.cancel_button)
        self.status_label = Gtk.Label(label="待機中")
        self.status_label.set_xalign(0)
        self.status_label.set_hexpand(True)
        bottom.append(self.status_label)

    @staticmethod
    def _append_form_row(grid: Gtk.Grid, row: int, label_text: str, child: Gtk.Widget) -> None:
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        label.set_width_chars(14)
        grid.attach(label, 0, row, 1, 1)
        child.set_hexpand(True)
        grid.attach(child, 1, row, 1, 1)

    # ------------------------------------------------------------------
    # Connection and server state
    # ------------------------------------------------------------------
    def _set_connection_status(self, text: str, connected: bool) -> None:
        self.connection_label.set_label(f"{text} ({self.api.base_url})")
        self.connection_label.remove_css_class("success")
        self.connection_label.remove_css_class("error")
        self.connection_label.add_css_class("success" if connected else "error")

    def _start_server_load(self) -> None:
        self._load_generation += 1
        generation = self._load_generation
        self._set_connection_status("接続中", False)
        self._set_error("")

        def worker() -> dict[str, Any]:
            result: dict[str, Any] = {"errors": []}
            try:
                self.api.health()
                result["health"] = True
            except ApiError as exc:
                result["errors"].append(f"接続: {exc}")
                return result
            for key, function in (
                ("profiles", self.api.get_profiles),
                ("profile_options", self.api.get_profile_options),
                ("ui_state", self.api.get_ui_state),
            ):
                try:
                    result[key] = function()
                except ApiError as exc:
                    result["errors"].append(f"{key}: {exc}")
            return result

        self._run_worker(worker, lambda result: self._on_server_load(generation, result), self._on_worker_error)

    def _on_server_load(self, generation: int, result: dict[str, Any]) -> bool:
        if generation != self._load_generation:
            return False
        errors = result.get("errors", [])
        if not result.get("health"):
            self._set_connection_status("未接続", False)
            self._set_error("サーバーへ接続できません。ポートとServerCLIの状態を確認してください。\n" + "\n".join(errors))
            return False
        self._set_connection_status("接続済み", True)
        if "profiles" in result:
            self._set_profiles(result["profiles"])
        if "profile_options" in result:
            self._set_batch_files(result["profile_options"])
        if "ui_state" in result:
            self._ui_state = UiState.from_json(result["ui_state"])
            self._restore_ui_state()
        if errors:
            self._set_error("一部のサーバー情報を取得できませんでした:\n" + "\n".join(errors))
        self._set_status("接続済み。入力ファイルを追加してください")
        self.logger.info("REST接続成功: %s", self.api.base_url)
        return False

    def _show_connection_dialog(self, _button: Gtk.Button) -> None:
        dialog = Gtk.Dialog(transient_for=self, modal=True)
        dialog.set_title("接続設定")
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        label = Gtk.Label(label="ServerCLI RESTポート（ループバックのみ）")
        label.set_xalign(0)
        content.append(label)
        entry = Gtk.Entry()
        entry.set_text(str(self.settings.rest_port))
        entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        content.append(entry)
        dialog.add_button("キャンセル", Gtk.ResponseType.CANCEL)
        dialog.add_button("接続", Gtk.ResponseType.OK)

        def response(_dialog: Gtk.Dialog, response_id: int) -> None:
            if response_id == Gtk.ResponseType.OK:
                try:
                    port = int(entry.get_text().strip())
                    base_url = make_loopback_url(port)
                    self.api.set_base_url(base_url)
                    self.settings.rest_port = port
                    save_settings(self.settings)
                    self._start_server_load()
                except (ValueError, OSError) as exc:
                    self._set_error(str(exc))
            dialog.destroy()

        dialog.connect("response", response)
        dialog.present()

    # ------------------------------------------------------------------
    # Input collection and file dialogs
    # ------------------------------------------------------------------
    def _on_drop(self, _target: Gtk.DropTarget, value: Any, _x: float, _y: float) -> bool:
        paths: list[str] = []
        rejected: list[RejectedPath] = []
        try:
            files = value.get_files()
        except (AttributeError, TypeError) as exc:
            self._set_error(f"ドロップされたファイル一覧を取得できません: {exc}")
            return False
        for file in files:
            path = file.get_path()
            if path:
                paths.append(path)
            else:
                rejected.append(RejectedPath(file.get_uri(), "ローカルファイルではありません"))
        self._start_collection(paths, rejected)
        return bool(paths or rejected)

    def _make_input_filter(self) -> Gtk.FileFilter:
        file_filter = Gtk.FileFilter()
        file_filter.set_name("TS入力（.ts / .m2t）")
        for pattern in ("*.ts", "*.TS", "*.m2t", "*.M2T"):
            file_filter.add_pattern(pattern)
        return file_filter

    def _new_file_dialog(self) -> Gtk.FileDialog:
        dialog = Gtk.FileDialog()
        dialog.set_title("入力TSファイルを選択")
        store = Gio.ListStore.new(Gtk.FileFilter)
        file_filter = self._make_input_filter()
        store.append(file_filter)
        dialog.set_filters(store)
        dialog.set_default_filter(file_filter)
        self._file_dialog = dialog
        return dialog

    def _choose_files(self, _button: Gtk.Button) -> None:
        dialog = self._new_file_dialog()
        dialog.open_multiple(self, None, self._on_files_selected)

    def _on_files_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            files = dialog.open_multiple_finish(result)
            paths = [files.get_item(index).get_path() for index in range(files.get_n_items())]
            self._start_collection([path for path in paths if path])
        except GLib.Error as exc:
            if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return
            self._set_error(f"ファイル選択に失敗しました: {exc}")
        except (TypeError, ValueError, AttributeError) as exc:
            self._set_error(f"ファイル選択結果を処理できません: {exc}")

    def _choose_folder(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("入力フォルダーを選択")
        self._file_dialog = dialog
        dialog.select_folder(self, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.select_folder_finish(result)
            path = file.get_path()
            self._start_collection([path] if path else [], [])
        except GLib.Error as exc:
            if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return
            self._set_error(f"フォルダー選択に失敗しました: {exc}")

    def _choose_output_folder(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("出力先フォルダーを選択")
        self._file_dialog = dialog
        dialog.select_folder(self, None, self._on_output_folder_selected)

    def _on_output_folder_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.select_folder_finish(result)
            path = file.get_path()
            if path:
                self.output_entry.set_text(path)
                self._set_error("")
        except GLib.Error as exc:
            if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return
            self._set_error(f"出力先フォルダー選択に失敗しました: {exc}")

    def _show_add_path_dialog(self, _button: Gtk.Button) -> None:
        dialog = Gtk.Dialog(transient_for=self, modal=True)
        dialog.set_title("入力パスを追加")
        content = dialog.get_content_area()
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        entry.set_placeholder_text("/path/to/input.ts またはフォルダー")
        content.append(entry)
        dialog.add_button("キャンセル", Gtk.ResponseType.CANCEL)
        dialog.add_button("追加", Gtk.ResponseType.OK)

        def response(_dialog: Gtk.Dialog, response_id: int) -> None:
            if response_id == Gtk.ResponseType.OK:
                self._start_collection([entry.get_text()], [])
            dialog.destroy()

        dialog.connect("response", response)
        dialog.present()

    def _start_collection(self, values: list[str], initial_rejected: list[RejectedPath]) -> None:
        if not values and not initial_rejected:
            return

        def worker() -> PathCollection:
            result = collect_paths(values)
            return PathCollection(
                accepted=result.accepted,
                rejected=list(initial_rejected) + result.rejected,
            )

        self._run_worker(worker, self._on_collection_complete, self._on_worker_error)

    def _on_collection_complete(self, result: PathCollection) -> bool:
        existing = set(self._input_paths)
        for path in result.accepted:
            if path not in existing:
                self._input_paths.append(path)
                existing.add(path)
        # 重複は再ドロップ時の通知だけであり、入力全体を無効にはしない。
        self._input_rejections.extend(
            item for item in result.rejected if item.reason != "重複したパスです"
        )
        self._rebuild_input_list()
        if self._input_rejections:
            message = "\n".join(f"{item.path}: {item.reason}" for item in self._input_rejections)
            self._set_error("除外した入力:\n" + message)
            self.logger.info("入力を除外: %s", message.replace("\n", " | "))
        else:
            self._set_error("")
        self._set_status(f"入力 {len(self._input_paths)}件")
        return False

    def _rebuild_input_list(self) -> None:
        child = self.input_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.input_list.remove(child)
            child = next_child
        for path in self._input_paths:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.set_margin_top(4)
            box.set_margin_bottom(4)
            box.set_margin_start(6)
            box.set_margin_end(6)
            label = Gtk.Label(label=path)
            label.set_xalign(0)
            label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            label.set_hexpand(True)
            box.append(label)
            remove_button = Gtk.Button(label="削除")
            remove_button.connect("clicked", lambda _button, value=path: self._remove_path(value))
            box.append(remove_button)
            row.set_child(box)
            self.input_list.append(row)

    def _remove_path(self, path: str) -> None:
        self._input_paths = [item for item in self._input_paths if item != path]
        self._rebuild_input_list()
        self._set_status(f"入力 {len(self._input_paths)}件")

    def _clear_paths(self, _button: Gtk.Button) -> None:
        self._input_paths.clear()
        self._input_rejections.clear()
        self._rebuild_input_list()
        self._set_error("")
        self._set_status("入力を消去しました")

    # ------------------------------------------------------------------
    # Form state and task submission
    # ------------------------------------------------------------------
    def _set_profiles(self, values: list[Any]) -> None:
        self._profiles = profile_names(values)
        self.profile_combo.remove_all()
        for name in self._profiles:
            self.profile_combo.append(name, name)
        if self._profiles and self.profile_combo.get_active_id() is None:
            self.profile_combo.set_active(0)

    def _set_batch_files(self, value: Any) -> None:
        self._batch_files = profile_option_pre_bat_files(value)
        self.batch_combo.remove_all()
        self.batch_combo.append("", "（なし）")
        for name in self._batch_files:
            self.batch_combo.append(name, name)
        self.batch_combo.set_active_id("")

    def _restore_ui_state(self) -> None:
        state = self._ui_state
        if state.last_used_profile and state.last_used_profile in self._profiles:
            self.profile_combo.set_active_id(state.last_used_profile)
        elif self._profiles and self.profile_combo.get_active_id() is None:
            self.profile_combo.set_active(0)
        if state.last_output_path and not self.output_entry.get_text().strip():
            self.output_entry.set_text(state.last_output_path)
        if state.last_add_queue_bat and state.last_add_queue_bat in self._batch_files:
            self.batch_combo.set_active_id(state.last_add_queue_bat)

    def _get_mode(self) -> ProcMode:
        value = self.mode_combo.get_active_id() or ProcMode.BATCH.value
        return ProcMode(value)

    def _get_priority(self) -> int:
        return int(self.priority_combo.get_active_id() or "3")

    def _submit(self, _button: Gtk.Button) -> None:
        if self._adding:
            return
        if self._input_rejections:
            message = "\n".join(f"{item.path}: {item.reason}" for item in self._input_rejections)
            self._set_error("除外した入力を確認してから再度追加してください:\n" + message)
            return
        self._set_error("")
        self._adding = True
        self._cancel_event = threading.Event()
        self._set_buttons_for_add(True)

        paths = list(self._input_paths)
        profile = self.profile_combo.get_active_id() or ""
        output_dir = self.output_entry.get_text()
        add_queue_bat = self.batch_combo.get_active_id() or ""
        try:
            mode = self._get_mode()
            priority = self._get_priority()
        except ValueError as exc:
            self._adding = False
            self._cancel_event = None
            self._set_buttons_for_add(False)
            self._set_error(str(exc))
            return

        def worker() -> Any:
            request = self.task_service.build_request(
                paths,
                profile=profile,
                output_dir=output_dir,
                priority=priority,
                mode=mode,
                add_queue_bat=add_queue_bat,
            )
            return self.task_service.submit(request, cancel_event=self._cancel_event)

        self._set_status(f"{len(paths)}件を追加処理中")
        self._run_worker(worker, self._on_submit_complete, self._on_submit_error)

    def _on_submit_complete(self, result: Any) -> bool:
        self._adding = False
        self._cancel_event = None
        self._set_buttons_for_add(False)
        response = result.response if hasattr(result, "response") else result
        message = response.get("message") if isinstance(response, dict) else None
        request_id = response.get("requestId") if isinstance(response, dict) else None
        self.logger.info("キュー追加成功 requestId=%s targets=%d", request_id, len(result.request.targets))
        self._input_paths.clear()
        self._input_rejections.clear()
        self._rebuild_input_list()
        self._set_error("")
        self._set_status(message or f"{len(result.request.targets)}件をキューへ追加しました")
        return False

    def _on_submit_error(self, error: BaseException) -> bool:
        self._adding = False
        self._cancel_event = None
        self._set_buttons_for_add(False)
        if isinstance(error, RequestCancelled):
            self._set_status("追加処理を停止しました")
        elif isinstance(error, (TaskAddError, ApiError)):
            self._set_error(str(error))
            self._set_status("追加できませんでした")
            self.logger.warning("キュー追加失敗: %s", error)
        else:
            self._set_error("予期しないエラーが発生しました: " + str(error))
            self._set_status("追加できませんでした")
            self.logger.error(
                "キュー追加中の予期しない例外",
                exc_info=(type(error), error, error.__traceback__),
            )
        return False

    def _cancel_add(self, _button: Gtk.Button) -> None:
        if not self._adding or self._cancel_event is None:
            return
        self._cancel_event.set()
        self.cancel_button.set_sensitive(False)
        self._set_status("サーバーへ追加停止を要求中")

        def worker() -> Any:
            return self.task_service.cancel_server_add()

        self._run_worker(worker, lambda _result: self._on_cancel_complete(), self._on_cancel_error)

    def _on_cancel_complete(self) -> bool:
        self._set_status("追加停止を要求しました（追加済み項目は残る場合があります）")
        return False

    def _on_cancel_error(self, error: BaseException) -> bool:
        self._set_error("追加停止要求に失敗しました: " + str(error))
        self.logger.warning("追加停止要求失敗: %s", error)
        return False

    def _set_buttons_for_add(self, adding: bool) -> None:
        self.add_button.set_sensitive(not adding)
        self.cancel_button.set_sensitive(adding)

    # ------------------------------------------------------------------
    # Thread helpers and lifecycle
    # ------------------------------------------------------------------
    def _run_worker(
        self,
        function: Callable[[], Any],
        on_success: Callable[[Any], Any],
        on_error: Callable[[BaseException], Any],
    ) -> None:
        def run() -> None:
            try:
                result = function()
            except BaseException as exc:  # worker errors must reach GTK visibly.
                GLib.idle_add(on_error, exc)
            else:
                GLib.idle_add(on_success, result)

        threading.Thread(target=run, daemon=True).start()

    def _on_worker_error(self, error: BaseException) -> bool:
        self._set_error(str(error))
        self.logger.error(
            "バックグラウンド処理の例外",
            exc_info=(type(error), error, error.__traceback__),
        )
        return False

    def _set_status(self, text: str) -> None:
        self.status_label.set_label(text)

    def _set_error(self, text: str) -> None:
        self.error_label.set_label(text)
        self.error_label.set_visible(bool(text))

    def _on_close_request(self, _window: Gtk.Window) -> bool:
        if self._allow_close:
            return False
        if self._adding:
            if self._close_dialog_open:
                return True
            self._close_dialog_open = True
            dialog = Gtk.AlertDialog()
            dialog.set_message("追加処理中です")
            dialog.set_detail("終了するとGUIは閉じますが、サーバー側で追加済みの項目は取り消されません。")
            dialog.set_buttons(["キャンセル", "終了"])
            dialog.set_cancel_button(0)
            dialog.set_default_button(0)

            def completed(_dialog: Gtk.AlertDialog, result: Gio.AsyncResult) -> None:
                self._close_dialog_open = False
                try:
                    choice = dialog.choose_finish(result)
                except GLib.Error:
                    return
                if choice == 1:
                    self._allow_close = True
                    self._save_window_size()
                    self.close()

            dialog.choose(self, None, completed)
            return True
        self._save_window_size()
        return False

    def _save_window_size(self) -> None:
        width = self.get_width()
        height = self.get_height()
        if width > 0:
            self.settings.window_width = width
        if height > 0:
            self.settings.window_height = height
        try:
            save_settings(self.settings)
        except OSError as exc:
            self.logger.warning("設定保存失敗: %s", exc)
