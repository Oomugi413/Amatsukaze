#!/bin/sh

# GTK/PyGObjectをOSのPythonから利用する。PyInstaller等でGTKを凍結しない。
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -f "${SCRIPT_DIR}/AmatsukazeLinuxGUI/amatsukaze_linux_gui.py" ]; then
    APP_DIR="${SCRIPT_DIR}/AmatsukazeLinuxGUI"
elif [ -f "${SCRIPT_DIR}/exe_files/AmatsukazeLinuxGUI/amatsukaze_linux_gui.py" ]; then
    APP_DIR="${SCRIPT_DIR}/exe_files/AmatsukazeLinuxGUI"
elif [ -f "${SCRIPT_DIR}/../amatsukaze_linux_gui.py" ]; then
    APP_DIR="${SCRIPT_DIR}/.."
else
    echo "AmatsukazeLinuxGUIのPythonファイルが見つかりません。" >&2
    exit 1
fi
PYTHON="/usr/bin/python3"

if [ ! -x "${PYTHON}" ]; then
    echo "${PYTHON} が見つかりません。python3をインストールしてください。" >&2
    exit 1
fi

if ! "${PYTHON}" -c 'import gi; gi.require_version("Gtk", "4.0")' >/dev/null 2>&1; then
    echo "PyGObjectまたはGTK 4が見つかりません。python3-gi gir1.2-gtk-4.0を確認してください。" >&2
    exit 1
fi

exec "${PYTHON}" "${APP_DIR}/amatsukaze_linux_gui.py" "$@"
