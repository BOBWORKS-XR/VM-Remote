#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script must be run on Linux."
  exit 1
fi

chmod +x "$ROOT_DIR/packaging/appimage/build.sh" "$ROOT_DIR/packaging/appimage/AppRun"
"$ROOT_DIR/packaging/appimage/build.sh"

echo "Done. AppImage is in: $ROOT_DIR/packaging/appimage/dist"
