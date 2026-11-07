import tempfile
import unittest
from pathlib import Path

from AmatsukazeLinuxGUI.amatsukaze_linux_gui.settings_service import GuiSettings, load_settings, save_settings


class SettingsServiceTests(unittest.TestCase):
    def test_round_trip_and_corrupt_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "settings.json"
            settings = GuiSettings(rest_port=12345, window_width=800, window_height=600)
            save_settings(settings, path)
            self.assertEqual(load_settings(path), settings)
            path.write_text("not-json", encoding="utf-8")
            self.assertEqual(load_settings(path), GuiSettings())


if __name__ == "__main__":
    unittest.main()

