import json
import unittest

from AmatsukazeLinuxGUI.amatsukaze_linux_gui.api_client import ApiClient, extract_error_message, is_loopback_url
from AmatsukazeLinuxGUI.amatsukaze_linux_gui.dto import AddQueueRequest, ProcMode, Target


class FakeResponse:
    def __init__(self, data: object, status: int = 200) -> None:
        self.status = status
        self._data = json.dumps(data, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._data

    def getcode(self) -> int:
        return self.status


class ApiClientTests(unittest.TestCase):
    def test_loopback_restriction(self) -> None:
        self.assertTrue(is_loopback_url("http://127.0.0.1:32769"))
        self.assertTrue(is_loopback_url("http://[::1]:32769"))
        self.assertFalse(is_loopback_url("http://192.0.2.1:32769"))
        self.assertFalse(is_loopback_url("http://127.0.0.1:32769/api"))

    def test_post_payload_uses_existing_queue_api_names(self) -> None:
        captured = {}

        def opener(request, timeout):
            captured["method"] = request.method
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse({"requestId": "abc", "message": "ok"})

        client = ApiClient("http://127.0.0.1:32769", opener=opener)
        request = AddQueueRequest(
            dir_path="/mnt",
            targets=[Target("/mnt/a.ts")],
            profile="標準",
            output_dir="/mnt/out",
            priority=3,
            mode=ProcMode.BATCH,
        )
        response = client.add_queue(request)
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["body"]["targets"][0]["path"], "/mnt/a.ts")
        self.assertEqual(captured["body"]["outputs"][0]["dstPath"], "/mnt/out")
        self.assertEqual(response["requestId"], "abc")

    def test_error_message_extracts_json_error(self) -> None:
        self.assertEqual(extract_error_message('{"error":"入力がありません"}'), "入力がありません")


if __name__ == "__main__":
    unittest.main()
