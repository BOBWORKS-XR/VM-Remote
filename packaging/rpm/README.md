# Fedora/RHEL (.rpm)

Build (on Fedora/RHEL):
1) `cd packaging/rpm`
2) `chmod +x build.sh`
3) `./build.sh`

Noob-friendly shortcut:
- Run `./packaging/release_rpm.sh` from repo root.

Dependencies:
- `python3`
- `python3-tkinter`

Output:
- `packaging/rpm/dist/vm-remote-<version>-1.noarch.rpm`
