#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="$ROOT_DIR/packaging/appimage/AppDir"
DIST_DIR="$ROOT_DIR/packaging/appimage/dist"
TOOLS_DIR="$ROOT_DIR/packaging/appimage/tools"
APP_ID="voicemeeter-deck"
APP_NAME="VM-Remote"
ARCH="$(uname -m)"

if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" ]]; then
  echo "Unsupported arch: $ARCH"
  exit 1
fi

VERSION="$(git -C "$ROOT_DIR" describe --tags --always 2>/dev/null || date +%Y%m%d)"

APPIMAGETOOL_BIN="$(command -v appimagetool || true)"
if [[ -z "$APPIMAGETOOL_BIN" ]]; then
  mkdir -p "$TOOLS_DIR"
  if [[ "$ARCH" == "x86_64" ]]; then
    APPIMAGETOOL_BIN="$TOOLS_DIR/appimagetool-x86_64.AppImage"
    APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  else
    APPIMAGETOOL_BIN="$TOOLS_DIR/appimagetool-aarch64.AppImage"
    APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-aarch64.AppImage"
  fi
  if [[ ! -x "$APPIMAGETOOL_BIN" ]]; then
    echo "Downloading appimagetool..."
    curl -L -o "$APPIMAGETOOL_BIN" "$APPIMAGETOOL_URL"
    chmod +x "$APPIMAGETOOL_BIN"
  fi
fi

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/bin" "$APP_DIR/usr/share/applications" \
  "$APP_DIR/usr/share/icons/hicolor/256x256/apps" "$DIST_DIR"

install -m 755 "$ROOT_DIR/linux-app/voicemeeter_deck.py" \
  "$APP_DIR/usr/bin/voicemeeter_deck.py"
install -m 644 "$ROOT_DIR/linux-app/logo.png" "$APP_DIR/usr/bin/logo.png"
install -m 644 "$ROOT_DIR/linux-app/icon.png" "$APP_DIR/usr/bin/icon.png"

cat > "$APP_DIR/usr/bin/$APP_ID" <<'EOF'
#!/usr/bin/env sh
HERE="$(dirname "$(readlink -f "$0")")"
exec python3 "$HERE/voicemeeter_deck.py"
EOF
chmod +x "$APP_DIR/usr/bin/$APP_ID"

install -m 755 "$ROOT_DIR/packaging/appimage/AppRun" "$APP_DIR/AppRun"
install -m 644 "$ROOT_DIR/packaging/appimage/voicemeeter-deck.desktop" \
  "$APP_DIR/usr/share/applications/voicemeeter-deck.desktop"
install -m 644 "$ROOT_DIR/linux-app/icon.png" \
  "$APP_DIR/usr/share/icons/hicolor/256x256/apps/voicemeeter-deck.png"

cp "$APP_DIR/usr/share/applications/voicemeeter-deck.desktop" \
  "$APP_DIR/voicemeeter-deck.desktop"
cp "$APP_DIR/usr/share/icons/hicolor/256x256/apps/voicemeeter-deck.png" \
  "$APP_DIR/voicemeeter-deck.png"

"$APPIMAGETOOL_BIN" "$APP_DIR" \
  "$DIST_DIR/${APP_NAME}-${VERSION}-${ARCH}.AppImage"

echo "AppImage created at: $DIST_DIR/${APP_NAME}-${VERSION}-${ARCH}.AppImage"
