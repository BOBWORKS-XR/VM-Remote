"""
Voicemeeter State Broadcaster
Runs on Windows PC to broadcast Voicemeeter state to Steam Deck via UDP
Uses Voicemeeter Remote API to read current state
"""

import ctypes
import time
import socket
import struct
import json
import sys
import os
from pathlib import Path

# Voicemeeter Remote API DLL paths
VM_DLL_PATHS = [
    r"C:\Program Files (x86)\VB\Voicemeeter\VoicemeeterRemote64.dll",
    r"C:\Program Files\VB\Voicemeeter\VoicemeeterRemote64.dll",
    os.path.expandvars(r"%ProgramFiles(x86)%\VB\Voicemeeter\VoicemeeterRemote64.dll"),
    os.path.expandvars(r"%ProgramFiles%\VB\Voicemeeter\VoicemeeterRemote64.dll"),
]

# Config
CONFIG_FILE = Path.home() / ".voicemeeter-broadcaster" / "config.json"
DEFAULT_CONFIG = {
    "deck_ip": "192.168.1.171",
    "broadcast_port": 6991,
    "poll_interval_ms": 50,
}


class VoicemeeterAPI:
    """Wrapper for Voicemeeter Remote API"""

    def __init__(self):
        self.dll = None
        self.connected = False
        self._load_dll()

    def _load_dll(self):
        """Load the Voicemeeter Remote DLL"""
        for path in VM_DLL_PATHS:
            if os.path.exists(path):
                try:
                    self.dll = ctypes.WinDLL(path)
                    print(f"Loaded DLL from: {path}")
                    self._setup_functions()
                    return
                except Exception as e:
                    print(f"Failed to load {path}: {e}")
        raise RuntimeError("Could not find VoicemeeterRemote64.dll")

    def _setup_functions(self):
        """Setup function signatures"""
        # Login/Logout
        self.dll.VBVMR_Login.restype = ctypes.c_long
        self.dll.VBVMR_Logout.restype = ctypes.c_long

        # Parameter access
        self.dll.VBVMR_IsParametersDirty.restype = ctypes.c_long
        self.dll.VBVMR_GetParameterFloat.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_float)]
        self.dll.VBVMR_GetParameterFloat.restype = ctypes.c_long

        # Levels
        self.dll.VBVMR_GetLevel.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.POINTER(ctypes.c_float)]
        self.dll.VBVMR_GetLevel.restype = ctypes.c_long

    def login(self) -> bool:
        """Connect to Voicemeeter"""
        result = self.dll.VBVMR_Login()
        if result == 0:
            self.connected = True
            print("Connected to Voicemeeter")
            return True
        elif result == 1:
            self.connected = True
            print("Connected to Voicemeeter (launched it)")
            return True
        else:
            print(f"Failed to connect to Voicemeeter: {result}")
            return False

    def logout(self):
        """Disconnect from Voicemeeter"""
        if self.connected:
            self.dll.VBVMR_Logout()
            self.connected = False

    def is_parameters_dirty(self) -> bool:
        """Check if parameters have changed"""
        return self.dll.VBVMR_IsParametersDirty() == 1

    def get_parameter(self, name: str) -> float:
        """Get a parameter value"""
        value = ctypes.c_float()
        result = self.dll.VBVMR_GetParameterFloat(name.encode(), ctypes.byref(value))
        if result == 0:
            return value.value
        return 0.0

    def get_level(self, level_type: int, channel: int) -> float:
        """Get audio level
        level_type: 0=pre-fader input, 1=post-fader input, 2=post-mute input, 3=output
        """
        value = ctypes.c_float()
        result = self.dll.VBVMR_GetLevel(level_type, channel, ctypes.byref(value))
        if result == 0:
            return value.value
        return -200.0

    def get_strip_state(self, index: int) -> dict:
        """Get full state of a strip"""
        prefix = f"Strip[{index}]"
        return {
            "gain": round(self.get_parameter(f"{prefix}.Gain")),
            "muted": self.get_parameter(f"{prefix}.Mute") > 0.5,
            "a1": self.get_parameter(f"{prefix}.A1") > 0.5,
            "a2": self.get_parameter(f"{prefix}.A2") > 0.5,
            "a3": self.get_parameter(f"{prefix}.A3") > 0.5,
            "b1": self.get_parameter(f"{prefix}.B1") > 0.5,
            "b2": self.get_parameter(f"{prefix}.B2") > 0.5,
        }

    def get_bus_state(self, index: int) -> dict:
        """Get full state of a bus"""
        prefix = f"Bus[{index}]"
        return {
            "gain": round(self.get_parameter(f"{prefix}.Gain")),
            "muted": self.get_parameter(f"{prefix}.Mute") > 0.5,
        }

    def get_strip_levels(self, index: int) -> tuple:
        """Get strip levels (left, right) in dB"""
        # Pre-fader input levels, 2 channels per strip
        left = self.get_level(0, index * 2)
        right = self.get_level(0, index * 2 + 1)
        return (left, right)

    def get_bus_levels(self, index: int) -> tuple:
        """Get bus levels (left, right) in dB"""
        # Output levels
        left = self.get_level(3, index * 8)  # 8 channels per bus
        right = self.get_level(3, index * 8 + 1)
        return (left, right)


class StateBroadcaster:
    """Broadcasts Voicemeeter state over UDP"""

    def __init__(self, deck_ip: str, port: int):
        self.deck_ip = deck_ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def broadcast_state(self, strips: list, buses: list, strip_levels: list, bus_levels: list):
        """Broadcast current state as JSON over UDP"""
        state = {
            "type": "vm_state",
            "strips": strips,
            "buses": buses,
            "strip_levels": strip_levels,
            "bus_levels": bus_levels,
        }

        data = json.dumps(state).encode("utf-8")
        try:
            self.socket.sendto(data, (self.deck_ip, self.port))
        except Exception as e:
            print(f"Broadcast error: {e}")


def load_config() -> dict:
    """Load or create config"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                config = DEFAULT_CONFIG.copy()
                config.update(json.load(f))
                return config
    except Exception as e:
        print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Save config"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def main():
    print("=" * 50)
    print("Voicemeeter State Broadcaster")
    print("=" * 50)

    # Load config
    config = load_config()

    # Get deck IP from command line or config
    if len(sys.argv) > 1:
        config["deck_ip"] = sys.argv[1]
        save_config(config)

    print(f"Broadcasting to: {config['deck_ip']}:{config['broadcast_port']}")
    print(f"Poll interval: {config['poll_interval_ms']}ms")
    print()

    # Initialize Voicemeeter API
    try:
        vm = VoicemeeterAPI()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        print("Make sure Voicemeeter is installed.")
        input("Press Enter to exit...")
        sys.exit(1)

    # Connect to Voicemeeter
    if not vm.login():
        print("ERROR: Could not connect to Voicemeeter")
        print("Make sure Voicemeeter is running.")
        input("Press Enter to exit...")
        sys.exit(1)

    # Create broadcaster
    broadcaster = StateBroadcaster(config["deck_ip"], config["broadcast_port"])

    print("Broadcasting state... Press Ctrl+C to stop.")
    print()

    try:
        last_strips = None
        last_buses = None

        while True:
            # Get current state
            strips = [vm.get_strip_state(i) for i in range(5)]
            buses = [vm.get_bus_state(i) for i in range(5)]

            # Get levels (convert to 0-100 scale)
            def db_to_percent(db):
                if db <= -60:
                    return 0.0
                elif db >= 0:
                    return 100.0
                else:
                    return (db + 60) / 60.0 * 100.0

            strip_levels = []
            for i in range(5):
                left, right = vm.get_strip_levels(i)
                strip_levels.append(db_to_percent(max(left, right)))

            bus_levels = []
            for i in range(5):
                left, right = vm.get_bus_levels(i)
                bus_levels.append(db_to_percent(max(left, right)))

            # Always broadcast (for levels), but print only on param changes
            if strips != last_strips or buses != last_buses:
                print(f"State changed - broadcasting update")
                last_strips = strips
                last_buses = buses

            broadcaster.broadcast_state(strips, buses, strip_levels, bus_levels)

            time.sleep(config["poll_interval_ms"] / 1000.0)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        vm.logout()
        print("Disconnected from Voicemeeter")


if __name__ == "__main__":
    main()
