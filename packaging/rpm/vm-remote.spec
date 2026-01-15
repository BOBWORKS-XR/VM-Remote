Name: vm-remote
Version: %{version}
Release: 1%{?dist}
Summary: VM Remote - Control Voicemeeter via VBAN
License: Proprietary
URL: https://github.com/BOBWORKS-XR/VM-Remote
Source0: %{name}-%{version}.tar.gz
BuildArch: noarch
Requires: python3, python3-tkinter

%description
VM Remote is a Linux remote control for Voicemeeter using VBAN.

%prep
%setup -q

%install
install -Dm755 linux-app/voicemeeter_deck.py %{buildroot}%{_datadir}/voicemeeter-deck/voicemeeter_deck.py
install -Dm644 linux-app/logo.png %{buildroot}%{_datadir}/voicemeeter-deck/logo.png
install -Dm644 linux-app/icon.png %{buildroot}%{_datadir}/voicemeeter-deck/icon.png
install -Dm755 packaging/rpm/voicemeeter-deck %{buildroot}%{_bindir}/voicemeeter-deck
install -Dm644 packaging/appimage/voicemeeter-deck.desktop %{buildroot}%{_datadir}/applications/voicemeeter-deck.desktop
install -Dm644 linux-app/icon.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/voicemeeter-deck.png

%files
%{_bindir}/voicemeeter-deck
%{_datadir}/voicemeeter-deck/voicemeeter_deck.py
%{_datadir}/voicemeeter-deck/logo.png
%{_datadir}/voicemeeter-deck/icon.png
%{_datadir}/applications/voicemeeter-deck.desktop
%{_datadir}/icons/hicolor/256x256/apps/voicemeeter-deck.png

%changelog
* Wed Jan 15 2026 BOBWORKS-XR - %{version}-1
- Auto-generated build
