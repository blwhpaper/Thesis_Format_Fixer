#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$ROOT_DIR/.pyinstaller}"
MACOS_ZIP_NAME="${MACOS_ZIP_NAME:-ThesisFormatFixer-macOS-unsigned.zip}"
export PYINSTALLER_CONFIG_DIR

cd "$ROOT_DIR"

mkdir -p "$PYINSTALLER_CONFIG_DIR"

"$PYTHON_BIN" -c "from pathlib import Path; import shutil; root = Path(r'$ROOT_DIR'); [shutil.rmtree(path) for path in (root / 'dist' / 'ThesisFormatFixer.app', root / 'dist' / 'ThesisFormatFixer') if path.exists()]; zip_path = root / 'dist' / r'$MACOS_ZIP_NAME'; zip_path.unlink(missing_ok=True)"

"$PYTHON_BIN" -m PyInstaller --noconfirm --clean packaging/pyinstaller.spec

BUNDLE_RULES_DIR="$ROOT_DIR/dist/ThesisFormatFixer.app/Contents/Resources/rules"
if [[ ! -d "$BUNDLE_RULES_DIR" ]]; then
  echo "Build failed: bundled rules directory missing: $BUNDLE_RULES_DIR" >&2
  exit 1
fi

BUNDLE_ICON="$ROOT_DIR/dist/ThesisFormatFixer.app/Contents/Resources/ThesisFormatFixer.icns"
if [[ ! -f "$BUNDLE_ICON" ]]; then
  echo "Build failed: bundled macOS icon missing: $BUNDLE_ICON" >&2
  exit 1
fi

ditto -c -k --keepParent "$ROOT_DIR/dist/ThesisFormatFixer.app" "$ROOT_DIR/dist/$MACOS_ZIP_NAME"

echo "Build completed."
echo "macOS app bundle: $ROOT_DIR/dist/ThesisFormatFixer.app"
echo "Unsigned trial zip: $ROOT_DIR/dist/$MACOS_ZIP_NAME"
echo "Bundled rules dir: $BUNDLE_RULES_DIR"
echo "Bundled icon file: $BUNDLE_ICON"
echo "PyInstaller cache dir: $PYINSTALLER_CONFIG_DIR"
