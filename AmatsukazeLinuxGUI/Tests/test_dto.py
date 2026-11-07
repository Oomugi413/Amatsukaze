import unittest

from AmatsukazeLinuxGUI.amatsukaze_linux_gui.dto import (
    AddQueueRequest,
    ProcMode,
    Target,
    profile_names,
)


class DtoTests(unittest.TestCase):
    def test_profile_names_accept_both_json_casing_and_deduplicate(self) -> None:
        values = [{"Name": "標準"}, {"name": "標準"}, {"NAME": "高画質"}, {"name": ""}]
        self.assertEqual(profile_names(values), ["標準", "高画質"])

    def test_add_queue_request_serializes_one_output_for_many_targets(self) -> None:
        request = AddQueueRequest(
            dir_path="/mnt/input",
            targets=[Target("/mnt/input/a.ts"), Target("/mnt/other/b.m2t")],
            profile="標準",
            output_dir="/mnt/output",
            priority=3,
            mode=ProcMode.BATCH,
            add_queue_bat=None,
        )
        payload = request.to_json()
        self.assertEqual(payload["mode"], "Batch")
        self.assertEqual([item["path"] for item in payload["targets"]], ["/mnt/input/a.ts", "/mnt/other/b.m2t"])
        self.assertEqual(len(payload["outputs"]), 1)
        self.assertEqual(payload["outputs"][0]["profile"], "標準")
        self.assertIsNone(payload["addQueueBat"])


if __name__ == "__main__":
    unittest.main()

