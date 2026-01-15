#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

chmod +x "$ROOT_DIR/packaging/deb/build.sh" "$ROOT_DIR/packaging/deb/voicemeeter-deck"
"$ROOT_DIR/packaging/deb/build.sh"
