import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class DesktopEntryTests(unittest.TestCase):
    def test_registers_and_uninstalls_user_desktop_entry(self) -> None:
        script = Path(__file__).parents[1] / "Packaging" / "install-desktop-entry.sh"
        with tempfile.TemporaryDirectory() as root:
            data_home = Path(root) / "XDG data home"
            environment = os.environ.copy()
            environment["XDG_DATA_HOME"] = str(data_home)
            environment["HOME"] = str(Path(root) / "home")

            registered = subprocess.run(
                [str(script)],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(registered.returncode, 0, registered.stderr)

            desktop_path = data_home / "applications" / "jp.amatsukaze.LinuxGUI.desktop"
            icon_path = data_home / "icons/hicolor/192x192/apps/amatsukaze-linux-gui.png"
            desktop = desktop_path.read_text(encoding="utf-8")
            self.assertIn("Type=Application", desktop)
            exec_line = next(
                line for line in desktop.splitlines() if line.startswith("Exec=")
            )
            self.assertTrue(exec_line.startswith("Exec=/"))
            self.assertIn("Icon=amatsukaze-linux-gui", desktop)
            self.assertIn("StartupWMClass=jp.amatsukaze.LinuxGUI", desktop)
            self.assertTrue(icon_path.is_file())

            unregistered = subprocess.run(
                [str(script), "--uninstall"],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(unregistered.returncode, 0, unregistered.stderr)
            self.assertFalse(desktop_path.exists())
            self.assertFalse(icon_path.exists())


if __name__ == "__main__":
    unittest.main()
