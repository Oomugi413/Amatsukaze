import os
import tempfile
import unittest
from pathlib import Path

from AmatsukazeLinuxGUI.amatsukaze_linux_gui.path_service import collect_paths, validate_output_directory


class PathServiceTests(unittest.TestCase):
    def test_collects_ts_and_m2t_but_excludes_m2ts(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "a.ts").write_bytes(b"")
            (directory / "b.m2t").write_bytes(b"")
            (directory / "upper.M2T").write_bytes(b"")
            (directory / "c.m2ts").write_bytes(b"")
            (directory / "d.txt").write_bytes(b"")
            result = collect_paths([str(directory)])
            self.assertEqual(
                result.accepted,
                [str(directory / "a.ts"), str(directory / "b.m2t"), str(directory / "upper.M2T")],
            )
            rejected = {Path(item.path).name: item.reason for item in result.rejected}
            self.assertIn("c.m2ts", rejected)
            self.assertIn("d.txt", rejected)

    def test_duplicate_paths_are_not_added_twice(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "input.ts")
            Path(path).write_bytes(b"")
            result = collect_paths([path, path])
            self.assertEqual(result.accepted, [os.path.abspath(path)])
            self.assertEqual(len(result.rejected), 1)

    def test_output_directory_can_be_created_later(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            output = str(Path(root) / "new-output")
            normalized, error = validate_output_directory(output)
            self.assertEqual(normalized, os.path.abspath(output))
            self.assertIsNone(error)
            file_path = Path(root) / "not-directory"
            file_path.write_text("x", encoding="utf-8")
            _, error = validate_output_directory(str(file_path))
            self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()
