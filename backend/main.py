"""
Voicemeeter Deck - Python Backend
Handles VBAN-Text protocol communication with Voicemeeter on Windows PC
"""

import os
import json
import socket
import struct
import decky

# VBAN Protocol Constants
VBAN_PROTOCOL_TXT = 0x40  # Text protocol (for commands)
VBAN_SR_MAXNUMBER = 0x00  # Sample rate index (not used for text)
VBAN_DATA_FORMAT = 0x10   # UTF-8 text format

# Default settings
DEFAULT_SETTINGS = {
    "pc_ip": "192.168.1.100",
    "vban_port": 6980,
    "stream_name": "Command1"
}


class VBANSender:
    """VBAN-Text protocol sender for Voicemeeter remote control"""

    HEADER_SIZE = 28

    def __init__(self, ip: str, port: int, stream_name: str = "Command1"):
        self.ip = ip
        self.port = port
        self.stream_name = stream_name
        self.frame_counter = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _build_header(self, text_length: int) -> bytes:
        """Build VBAN header for text protocol"""
        header = bytearray(self.HEADER_SIZE)
        header[0:4] = b"VBAN"
        header[4] = VBAN_SR_MAXNUMBER | VBAN_PROTOCOL_TXT  # 0x40 for text
        header[5] = 0  # padding
        header[6] = 0  # channel
        header[7] = VBAN_DATA_FORMAT  # 0x10 for UTF-8
        stream_bytes = self.stream_name.encode("utf-8")[:16]
        header[8:8 + len(stream_bytes)] = stream_bytes
        header[24:28] = struct.pack("<I", self.frame_counter)
        self.frame_counter = (self.frame_counter + 1) % 0xFFFFFFFF
        return bytes(header)

    def send_command(self, command: str) -> bool:
        """Send a VBAN-Text command to Voicemeeter"""
        try:
            text_bytes = command.encode("ascii")
            header = self._build_header(len(text_bytes))
            packet = header + text_bytes
            self.socket.sendto(packet, (self.ip, self.port))
            decky.logger.info(f"Sent VBAN command: {command}")
            return True
        except Exception as e:
            decky.logger.error(f"Error sending VBAN command: {e}")
            return False

    def close(self):
        """Close the socket"""
        self.socket.close()


class Plugin:
    vban_sender = None
    strip_mute_states = {}
    bus_mute_states = {}

    def _get_settings_file(self):
        return os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "settings.json")

    def _load_settings(self) -> dict:
        """Load settings from file or return defaults"""
        try:
            settings_file = self._get_settings_file()
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            decky.logger.error(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

    def _save_settings_to_file(self, settings: dict) -> None:
        """Save settings to file"""
        try:
            settings_file = self._get_settings_file()
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            decky.logger.error(f"Error saving settings: {e}")

    def _get_vban_sender(self) -> VBANSender:
        """Get or create VBAN sender with current settings"""
        if self.vban_sender is None:
            settings = self._load_settings()
            self.vban_sender = VBANSender(
                settings["pc_ip"],
                settings["vban_port"],
                settings["stream_name"]
            )
        return self.vban_sender

    def _recreate_vban_sender(self):
        """Recreate VBAN sender with new settings"""
        if self.vban_sender is not None:
            self.vban_sender.close()
        settings = self._load_settings()
        self.vban_sender = VBANSender(
            settings["pc_ip"],
            settings["vban_port"],
            settings["stream_name"]
        )

    # Lifecycle methods
    async def _main(self):
        """Plugin entry point"""
        decky.logger.info("Voicemeeter Deck plugin loaded!")

    async def _unload(self):
        """Plugin cleanup"""
        if self.vban_sender is not None:
            self.vban_sender.close()
            self.vban_sender = None
        decky.logger.info("Voicemeeter Deck plugin unloaded!")

    # Callable methods exposed to frontend
    async def get_settings(self) -> dict:
        """Get current settings"""
        return self._load_settings()

    async def save_settings(self, settings: dict) -> None:
        """Save settings and recreate VBAN sender"""
        self._save_settings_to_file(settings)
        self._recreate_vban_sender()

    async def set_strip_param(self, strip_index: int, param: str, value: float) -> bool:
        """Set a parameter on a strip"""
        sender = self._get_vban_sender()
        command = f"Strip[{strip_index}].{param}={value};"
        return sender.send_command(command)

    async def set_bus_param(self, bus_index: int, param: str, value: float) -> bool:
        """Set a parameter on a bus"""
        sender = self._get_vban_sender()
        command = f"Bus[{bus_index}].{param}={value};"
        return sender.send_command(command)

    async def toggle_strip_mute(self, strip_index: int) -> bool:
        """Toggle mute on a strip"""
        current_state = self.strip_mute_states.get(strip_index, False)
        new_state = not current_state
        self.strip_mute_states[strip_index] = new_state
        sender = self._get_vban_sender()
        command = f"Strip[{strip_index}].Mute={1 if new_state else 0};"
        return sender.send_command(command)

    async def toggle_bus_mute(self, bus_index: int) -> bool:
        """Toggle mute on a bus"""
        current_state = self.bus_mute_states.get(bus_index, False)
        new_state = not current_state
        self.bus_mute_states[bus_index] = new_state
        sender = self._get_vban_sender()
        command = f"Bus[{bus_index}].Mute={1 if new_state else 0};"
        return sender.send_command(command)

    async def test_connection(self) -> bool:
        """Test connection by sending a no-op command"""
        try:
            sender = self._get_vban_sender()
            return sender.send_command("Command.Restart=0;")
        except Exception as e:
            decky.logger.error(f"Connection test failed: {e}")
            return False
