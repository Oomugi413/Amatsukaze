#!/usr/bin/env python3
"""Executable entry point for AmatsukazeLinuxGUI."""

from __future__ import annotations

import sys
from pathlib import Path


# 配布物ではこのスクリプトが AmatsukazeLinuxGUI/ の中に置かれるため、
# 親ディレクトリをimport検索パスへ追加して同じ絶対importを使う。
_package_root = Path(__file__).resolve().parent.parent
if str(_package_root) not in sys.path:
    sys.path.insert(0, str(_package_root))

from AmatsukazeLinuxGUI.amatsukaze_linux_gui.application import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

