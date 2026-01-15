#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOPDIR="$ROOT_DIR/packaging/rpm/rpmbuild"
SOURCES="$TOPDIR/SOURCES"
SPECS="$TOPDIR/SPECS"
DIST_DIR="$ROOT_DIR/packaging/rpm/dist"
VERSION="$(git -C "$ROOT_DIR" describe --tags --always 2>/dev/null || date +%Y%m%d)"

rm -rf "$TOPDIR"
mkdir -p "$SOURCES" "$SPECS" "$DIST_DIR"

tar -czf "$SOURCES/vm-remote-$VERSION.tar.gz" \
  -C "$ROOT_DIR" linux-app packaging/appimage packaging/rpm

cp "$ROOT_DIR/packaging/rpm/vm-remote.spec" "$SPECS/vm-remote.spec"

rpmbuild --define "_topdir $TOPDIR" --define "version $VERSION" -ba "$SPECS/vm-remote.spec"

find "$TOPDIR/RPMS" -name "*.rpm" -exec cp {} "$DIST_DIR/" \;

echo "RPM package created in: $DIST_DIR"
