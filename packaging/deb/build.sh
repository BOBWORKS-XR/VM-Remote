#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG_DIR="$ROOT_DIR/packaging/deb/pkgroot"
DIST_DIR="$ROOT_DIR/packaging/deb/dist"
VERSION="$(git -C "$ROOT_DIR" describe --tags --always 2>/dev/null || date +%Y%m%d)"

rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN" "$DIST_DIR"

cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: vm-remote
Version: $VERSION
Section: sound
Priority: optional
Architecture: all
Maintainer: BOBWORKS-XR
Depends: python3, python3-tk
Homepage: https://github.com/BOBWORKS-XR/VM-Remote
Description: VM Remote - Control Voicemeeter via VBAN
 A Linux remote control for Voicemeeter using VBAN.
EOF

install -Dm755 "$ROOT_DIR/linux-app/voicemeeter_deck.py" \
  "$PKG_DIR/usr/share/voicemeeter-deck/voicemeeter_deck.py"
install -Dm644 "$ROOT_DIR/linux-app/logo.png" \
  "$PKG_DIR/usr/share/voicemeeter-deck/logo.png"
install -Dm644 "$ROOT_DIR/linux-app/icon.png" \
  "$PKG_DIR/usr/share/voicemeeter-deck/icon.png"
install -Dm755 "$ROOT_DIR/packaging/deb/voicemeeter-deck" \
  "$PKG_DIR/usr/bin/voicemeeter-deck"
install -Dm644 "$ROOT_DIR/packaging/appimage/voicemeeter-deck.desktop" \
  "$PKG_DIR/usr/share/applications/voicemeeter-deck.desktop"
install -Dm644 "$ROOT_DIR/linux-app/icon.png" \
  "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/voicemeeter-deck.png"

dpkg-deb --build "$PKG_DIR" "$DIST_DIR/vm-remote_${VERSION}_all.deb"

echo "Deb package created at: $DIST_DIR/vm-remote_${VERSION}_all.deb"
