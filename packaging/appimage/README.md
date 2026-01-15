# AppImage (system Python)

This packaging uses the system `python3` and `tkinter` on the target machine.
It produces a single AppImage file without changing the app source.

Build (on Linux):
1) `cd packaging/appimage`
2) `chmod +x build.sh AppRun`
3) `./build.sh`

Noob-friendly shortcut:
- Run `./packaging/release_appimage.sh` from repo root.

Output:
- `packaging/appimage/dist/VM-Remote-<version>-<arch>.AppImage`

Runtime requirements (target machine):
- `python3`
- `python3-tk`

Notes:
- If `appimagetool` is not installed, `build.sh` will download it into
  `packaging/appimage/tools/`.
