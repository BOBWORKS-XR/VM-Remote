# Flatpak

Build (on Linux):
1) `cd packaging/flatpak`
2) `chmod +x build.sh`
3) `./build.sh`

Noob-friendly shortcut:
- Run `./packaging/release_flatpak.sh` from repo root.

Notes:
- This Flatpak uses `org.freedesktop.Sdk` as the runtime to get Python/Tk.
- Network access is enabled for VBAN.
- Output: `packaging/flatpak/dist/VM-Remote-<version>.flatpak`
