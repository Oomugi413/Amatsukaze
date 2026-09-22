#!/bin/sh

# XDGのユーザー領域へ、配布物の実パスを埋め込んだ.desktopを登録する。
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PACKAGE_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
DESKTOP_ID="jp.amatsukaze.LinuxGUI.desktop"
ICON_NAME="amatsukaze-linux-gui"

if [ -n "${XDG_DATA_HOME:-}" ]; then
    DATA_HOME=$(CDPATH= cd -- "${XDG_DATA_HOME}" 2>/dev/null && pwd) || DATA_HOME="${XDG_DATA_HOME}"
else
    if [ -z "${HOME:-}" ]; then
        echo "HOMEまたはXDG_DATA_HOMEが設定されていません。" >&2
        exit 1
    fi
    DATA_HOME="${HOME}/.local/share"
fi

APPLICATION_DIR="${DATA_HOME}/applications"
ICON_DIR="${DATA_HOME}/icons/hicolor/192x192/apps"
DESKTOP_PATH="${APPLICATION_DIR}/${DESKTOP_ID}"
ICON_PATH="${ICON_DIR}/${ICON_NAME}.png"
TEMPLATE_PATH="${PACKAGE_DIR}/Packaging/AmatsukazeLinuxGUI.desktop.in"
SOURCE_ICON_PATH="${PACKAGE_DIR}/Assets/${ICON_NAME}.png"

usage() {
    echo "Usage: $0 [--uninstall]" >&2
}

refresh_desktop_database() {
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${APPLICATION_DIR}" >/dev/null 2>&1 || true
    fi
}

if [ "${1:-}" = "--uninstall" ]; then
    if [ "$#" -ne 1 ]; then
        usage
        exit 2
    fi
    rm -f "${DESKTOP_PATH}" "${ICON_PATH}"
    refresh_desktop_database
    echo "Amatsukaze Linux GUIのアプリ一覧登録を削除しました。"
    exit 0
fi

if [ "$#" -ne 0 ]; then
    usage
    exit 2
fi

if [ ! -f "${TEMPLATE_PATH}" ] || [ ! -f "${SOURCE_ICON_PATH}" ]; then
    echo "デスクトップエントリのテンプレートまたはアイコンが見つかりません。" >&2
    exit 1
fi

# 配布物の場所に応じて、アプリ一覧から実行するランチャーを選択する。
if [ -x "${PACKAGE_DIR}/../../AmatsukazeLinuxGUI.sh" ]; then
    EXEC_PATH=$(CDPATH= cd -- "${PACKAGE_DIR}/../.." && pwd)/AmatsukazeLinuxGUI.sh
elif [ -x "${PACKAGE_DIR}/Packaging/AmatsukazeLinuxGUI.sh" ]; then
    EXEC_PATH="${PACKAGE_DIR}/Packaging/AmatsukazeLinuxGUI.sh"
else
    echo "AmatsukazeLinuxGUI.shが見つかりません。" >&2
    exit 1
fi

# .desktopの文字列値には制御文字を記述できないため、配布物のパスに
# 改行やタブが含まれる場合は、壊れたエントリを作らず明示的に中止する。
if printf '%s' "${EXEC_PATH}" | LC_ALL=C grep -q '[[:cntrl:]]'; then
    echo "AmatsukazeLinuxGUIのパスに.desktopで使用できない制御文字が含まれています。" >&2
    exit 1
fi

# .desktopのExec引数はシェルで解釈されないため、予約文字を仕様どおりエスケープする。
escape_exec_argument() {
    # sedの正規表現では「*」などの扱いが処理系差異を生みやすいため、
    # 1文字ずつ走査してデスクトップエントリの予約文字をエスケープする。
    # パスは通常改行を含まないため、標準入力を1行として処理する。
    printf '%s' "$1" | LC_ALL=C awk '
        {
            for (position = 1; position <= length($0); ++position) {
                character = substr($0, position, 1)
                if (character == "%") {
                    printf "%%%%"
                } else if (character == "\\" || character == " " || character == "\t" ||
                           character == "\"" || character == "\047" || character == "`" ||
                           character == "$" || character == ";" || character == "&" ||
                           character == "|" || character == "<" || character == ">" ||
                           character == "(" || character == ")" || character == "*" ||
                           character == "?" || character == "#" || character == "~") {
                    printf "\\%s", character
                } else {
                    printf "%s", character
                }
            }
        }
    '
}

EXEC_VALUE=$(escape_exec_argument "${EXEC_PATH}")
export EXEC_VALUE
mkdir -p "${APPLICATION_DIR}" "${ICON_DIR}"
temporary_desktop=$(mktemp "${APPLICATION_DIR}/.${DESKTOP_ID}.XXXXXX")
cleanup() {
    rm -f "${temporary_desktop}"
}
trap cleanup EXIT HUP INT TERM

awk '
    $0 == "Exec=@EXEC@" {
        print "Exec=" ENVIRON["EXEC_VALUE"]
        next
    }
    { print }
' "${TEMPLATE_PATH}" >"${temporary_desktop}"
chmod 0644 "${temporary_desktop}"
install -m 0644 "${temporary_desktop}" "${DESKTOP_PATH}"
install -m 0644 "${SOURCE_ICON_PATH}" "${ICON_PATH}"
refresh_desktop_database

echo "Amatsukaze Linux GUIをアプリ一覧へ登録しました: ${DESKTOP_PATH}"
