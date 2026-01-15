#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

chmod +x "$ROOT_DIR/packaging/rpm/build.sh" "$ROOT_DIR/packaging/rpm/voicemeeter-deck"
"$ROOT_DIR/packaging/rpm/build.sh"
