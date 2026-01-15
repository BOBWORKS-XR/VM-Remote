#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$ROOT_DIR/packaging/flatpak/io.github.bobworksx.VMRemote.yml"
BUILD_DIR="$ROOT_DIR/packaging/flatpak/build"
REPO_DIR="$ROOT_DIR/packaging/flatpak/repo"
DIST_DIR="$ROOT_DIR/packaging/flatpak/dist"
APP_ID="io.github.bobworksx.VMRemote"
VERSION="$(git -C "$ROOT_DIR" describe --tags --always 2>/dev/null || date +%Y%m%d)"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script must be run on Linux."
  exit 1
fi

mkdir -p "$DIST_DIR"

flatpak-builder --force-clean --repo="$REPO_DIR" "$BUILD_DIR" "$MANIFEST"
flatpak build-bundle "$REPO_DIR" "$DIST_DIR/VM-Remote-$VERSION.flatpak" "$APP_ID"

echo "Flatpak created at: $DIST_DIR/VM-Remote-$VERSION.flatpak"
