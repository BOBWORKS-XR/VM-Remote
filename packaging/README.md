# Packaging

This folder contains release packaging for common Linux formats. The app source
stays in `linux-app/`; these files only build release artifacts.

## One-shot release scripts (run from repo root)

- AppImage: `./packaging/release_appimage.sh`
- Flatpak: `./packaging/release_flatpak.sh`
- Debian/Ubuntu: `./packaging/release_deb.sh`
- Fedora/RHEL: `./packaging/release_rpm.sh`
- Arch/SteamOS (AUR): `./packaging/release_aur.sh`

## Build dependencies

- AppImage: `bash`, `curl`
- Flatpak: `flatpak`, `flatpak-builder`
- Debian/Ubuntu: `dpkg-deb`
- Fedora/RHEL: `rpmbuild` (rpm-build)
- Arch/SteamOS: `base-devel`, `git`

## Runtime dependencies

- AppImage / deb / rpm / AUR: `python3` and `tkinter`
- Flatpak: bundled via `org.freedesktop.Sdk`
