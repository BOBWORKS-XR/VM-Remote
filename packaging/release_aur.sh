#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUR_DIR="$ROOT_DIR/packaging/aur"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script must be run on Linux."
  exit 1
fi

cd "$AUR_DIR"
makepkg -f --noconfirm
makepkg --printsrcinfo > .SRCINFO

echo "AUR package and .SRCINFO created in: $AUR_DIR"
