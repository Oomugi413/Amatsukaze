import tempfile
import unittest
from pathlib import Path

from AmatsukazeLinuxGUI.amatsukaze_linux_gui.dto import ProcMode
from AmatsukazeLinuxGUI.amatsukaze_linux_gui.api_client import ApiClient
from AmatsukazeLinuxGUI.amatsukaze_linux_gui.task_add_service import TaskAddError, TaskAddService, build_add_queue_request


class TaskAddServiceTests(unittest.TestCase):
    def test_builds_one_request_for_files_in_different_directories(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            first = Path(root) / "a" / "first.ts"
            second = Path(root) / "b" / "second.m2t"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_bytes(b"")
            second.write_bytes(b"")
            request = build_add_queue_request(
                [str(first), str(second)],
                profile="標準",
                output_dir=str(Path(root) / "out"),
                priority=4,
                mode=ProcMode.TEST,
                add_queue_bat="pre.sh",
            )
            self.assertEqual(len(request.targets), 2)
            self.assertEqual(request.dir_path, str(first.parent))
            self.assertEqual(request.mode, ProcMode.TEST)
            self.assertEqual(request.add_queue_bat, "pre.sh")

    def test_empty_inputs_and_required_fields_are_rejected(self) -> None:
        with self.assertRaises(TaskAddError):
            build_add_queue_request([], profile="標準", output_dir="/tmp", priority=3, mode=ProcMode.BATCH)
        with self.assertRaises(TaskAddError):
            build_add_queue_request(["/tmp/input.ts"], profile="", output_dir="/tmp", priority=3, mode=ProcMode.BATCH)

    def test_service_revalidates_files_before_sending(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "input.m2ts"
            path.write_bytes(b"")
            service = TaskAddService(ApiClient("http://127.0.0.1:32769"))
            with self.assertRaises(TaskAddError):
                service.build_request(
                    [str(path)],
                    profile="標準",
                    output_dir=root,
                    priority=3,
                    mode=ProcMode.BATCH,
                )


if __name__ == "__main__":
    unittest.main()
