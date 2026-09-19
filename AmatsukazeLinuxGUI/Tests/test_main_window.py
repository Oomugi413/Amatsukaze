import unittest

try:
    from AmatsukazeLinuxGUI.amatsukaze_linux_gui.main_window import MainWindow
except (ImportError, ValueError):
    # GTK 4/PyGObjectがないビルド環境では、GUIコールバックのテストだけを省略する。
    MainWindow = None


class _FakeFile:
    def __init__(self, path: str | None) -> None:
        self._path = path

    def get_path(self) -> str | None:
        return self._path


class _FakeFileList:
    def __init__(self, paths: list[str | None]) -> None:
        self._files = [_FakeFile(path) for path in paths]

    def get_n_items(self) -> int:
        return len(self._files)

    def get_item(self, index: int) -> _FakeFile:
        return self._files[index]


class _FakeDialog:
    def __init__(self, paths: list[str | None]) -> None:
        self._files = _FakeFileList(paths)

    def open_multiple_finish(self, _result: object) -> _FakeFileList:
        return self._files


class _FakeWindow:
    def __init__(self) -> None:
        self.collection: tuple[list[str], list[object]] | None = None
        self.error = ""

    def _start_collection(self, values: list[str], rejected: list[object]) -> None:
        self.collection = (values, rejected)

    def _set_error(self, message: str) -> None:
        self.error = message


@unittest.skipIf(MainWindow is None, "GTK 4/PyGObjectが利用できません")
class MainWindowTests(unittest.TestCase):
    def test_file_selection_starts_collection_without_initial_rejections(self) -> None:
        window = _FakeWindow()
        dialog = _FakeDialog(["/mnt/first.ts", None, "/mnt/second.m2t"])

        MainWindow._on_files_selected(window, dialog, object())

        self.assertEqual(
            window.collection,
            (["/mnt/first.ts", "/mnt/second.m2t"], []),
        )
        self.assertEqual(window.error, "")


if __name__ == "__main__":
    unittest.main()
