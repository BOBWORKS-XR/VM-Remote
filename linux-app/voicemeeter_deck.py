#!/usr/bin/env python3
"""
Voicemeeter Deck - Linux/Steam Deck App
Control Voicemeeter via VBAN from your Steam Deck
"""

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import struct
import json
import threading
import time
import sys
import traceback
from pathlib import Path

# Try to import PIL for logo support
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# VBAN Protocol Constants
VBAN_PROTOCOL_TXT = 0x40
VBAN_PROTOCOL_SERVICE = 0x60
VBAN_DATA_FORMAT = 0x10
VBAN_SERVICE_RTPACKETREGISTER = 32
VBAN_SERVICE_RTPACKET = 33

# RT packet state bit masks
VMRTSTATE_MODE_MUTE = 0x00000001
VMRTSTATE_MODE_BUSA1 = 0x00001000
VMRTSTATE_MODE_BUSA2 = 0x00002000
VMRTSTATE_MODE_BUSA3 = 0x00004000
VMRTSTATE_MODE_BUSA4 = 0x00008000
VMRTSTATE_MODE_BUSA5 = 0x00080000
VMRTSTATE_MODE_BUSB1 = 0x00010000
VMRTSTATE_MODE_BUSB2 = 0x00020000
VMRTSTATE_MODE_BUSB3 = 0x00040000

ROUTING_STATE_BITS = {
    "A1": VMRTSTATE_MODE_BUSA1,
    "A2": VMRTSTATE_MODE_BUSA2,
    "A3": VMRTSTATE_MODE_BUSA3,
    "A4": VMRTSTATE_MODE_BUSA4,
    "A5": VMRTSTATE_MODE_BUSA5,
    "B1": VMRTSTATE_MODE_BUSB1,
    "B2": VMRTSTATE_MODE_BUSB2,
    "B3": VMRTSTATE_MODE_BUSB3,
}

VM_TYPE_TO_PROFILE = {
    1: "standard",
    2: "banana",
    3: "potato",
    6: "potato",
}

MIXER_PROFILES = {
    "standard": {
        "strip_labels": ["HW 1", "HW 2", "Virt 1"],
        "hardware_strips": 2,
        "bus_labels": ["A", "B"],
        "routing_buses": [("A1", "A"), ("B1", "B")],
    },
    "banana": {
        "strip_labels": ["HW 1", "HW 2", "HW 3", "Virt 1", "Virt 2"],
        "hardware_strips": 3,
        "bus_labels": ["A1", "A2", "A3", "B1", "B2"],
        "routing_buses": [("A1", "A1"), ("A2", "A2"), ("A3", "A3"), ("B1", "B1"), ("B2", "B2")],
    },
    "potato": {
        "strip_labels": ["HW 1", "HW 2", "HW 3", "HW 4", "HW 5", "Virt 1", "Virt 2", "Virt 3"],
        "hardware_strips": 5,
        "bus_labels": ["A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3"],
        "routing_buses": [
            ("A1", "A1"),
            ("A2", "A2"),
            ("A3", "A3"),
            ("A4", "A4"),
            ("A5", "A5"),
            ("B1", "B1"),
            ("B2", "B2"),
            ("B3", "B3"),
        ],
    },
}

# UI Colors - dark gray theme
BG_COLOR = "#2d2d2d"  # Main background - lighter black/dark gray
BG_DARKER = "#252525"  # Slightly darker for contrast
LOGO_SCALE = 5
LOGO_MAX_HEIGHT_RATIO = 0.175

CONFIG_FILE = Path.home() / ".config" / "voicemeeter-deck" / "config.json"

DEFAULT_CONFIG = {
    "pc_ip": "192.168.1.212",
    "port": 6980,
    "stream_name": "Command1",
    "mixer_type": "auto",
    "strips": {},
    "buses": {},
    "recorder": {"play": False, "record": False, "pause": False}
}

def _log_exception(exc_type, exc_value, exc_traceback):
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log_path = CONFIG_FILE.parent / "crash.log"
        with open(log_path, "a", encoding="utf-8") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n[{timestamp}] Unhandled exception\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = _log_exception


class VBANSender:
    """Send VBAN text commands to Voicemeeter"""

    def __init__(self, ip: str, port: int, stream_name: str):
        self.ip = ip
        self.port = port
        self.stream_name = stream_name
        self.frame_counter = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_command(self, command: str) -> bool:
        """Send a VBAN text command"""
        try:
            header = bytearray(28)
            header[0:4] = b"VBAN"
            header[4] = VBAN_PROTOCOL_TXT
            header[5] = 0
            header[6] = 0
            header[7] = VBAN_DATA_FORMAT
            stream_bytes = self.stream_name.encode("utf-8")[:16]
            header[8:8 + len(stream_bytes)] = stream_bytes
            header[24:28] = struct.pack("<I", self.frame_counter)
            self.frame_counter = (self.frame_counter + 1) % 0xFFFFFFFF

            packet = bytes(header) + command.encode("utf-8")
            self.socket.sendto(packet, (self.ip, self.port))
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False

    def set_strip_gain(self, index: int, gain: float):
        self.send_command(f"Strip[{index}].Gain={gain};")

    def set_strip_mute(self, index: int, muted: bool):
        self.send_command(f"Strip[{index}].Mute={1 if muted else 0};")

    def set_strip_bus(self, index: int, bus: str, enabled: bool):
        bus = bus.upper()
        self.send_command(f"Strip[{index}].{bus}={1 if enabled else 0};")

    def set_strip_a1(self, index: int, enabled: bool):
        self.set_strip_bus(index, "A1", enabled)

    def set_strip_a2(self, index: int, enabled: bool):
        self.set_strip_bus(index, "A2", enabled)

    def set_strip_a3(self, index: int, enabled: bool):
        self.set_strip_bus(index, "A3", enabled)

    def set_strip_a4(self, index: int, enabled: bool):
        self.set_strip_bus(index, "A4", enabled)

    def set_strip_a5(self, index: int, enabled: bool):
        self.set_strip_bus(index, "A5", enabled)

    def set_strip_b1(self, index: int, enabled: bool):
        self.set_strip_bus(index, "B1", enabled)

    def set_strip_b2(self, index: int, enabled: bool):
        self.set_strip_bus(index, "B2", enabled)

    def set_strip_b3(self, index: int, enabled: bool):
        self.set_strip_bus(index, "B3", enabled)

    def set_strip_gate(self, index: int, value: float):
        # Gate value 0-10 maps to threshold
        self.send_command(f"Strip[{index}].Gate={value};")

    def set_strip_eq_bass(self, index: int, value: float):
        # EQ bass: -12 to +12
        self.send_command(f"Strip[{index}].EQGain1={value};")

    def set_strip_eq_mid(self, index: int, value: float):
        # EQ mid: -12 to +12
        self.send_command(f"Strip[{index}].EQGain2={value};")

    def set_strip_eq_treble(self, index: int, value: float):
        # EQ treble: -12 to +12
        self.send_command(f"Strip[{index}].EQGain3={value};")

    def set_bus_gain(self, index: int, gain: float):
        self.send_command(f"Bus[{index}].Gain={gain};")

    def set_bus_mute(self, index: int, muted: bool):
        self.send_command(f"Bus[{index}].Mute={1 if muted else 0};")

    # Tape recorder controls
    def recorder_play(self):
        self.send_command("Recorder.Play=1;")

    def recorder_stop(self):
        self.send_command("Recorder.Stop=1;")

    def recorder_record(self):
        self.send_command("Recorder.Record=1;")

    def recorder_pause(self):
        self.send_command("Recorder.Pause=1;")

    def recorder_rewind(self):
        self.send_command("Recorder.Rewind=1;")

    def recorder_forward(self):
        self.send_command("Recorder.Forward=1;")

    def recorder_goto_start(self):
        self.send_command("Recorder.GoTo=0;")

    def register_rt_packet(self, timeout: int = 15, stream_name: str = "VMDeckLinux", source_socket=None):
        """Register for RT-Packet updates (must be called periodically every ~10s).

        Pass the listener socket so Voicemeeter replies to the correct UDP port.
        """
        try:
            header = bytearray(28)
            header[0:4] = b"VBAN"
            # format_SR (byte 4): Contains protocol (0x60) + sample rate bits
            header[4] = VBAN_PROTOCOL_SERVICE  # 0x60
            # format_nbs (byte 5): Number of samples (0 for service packets)
            header[5] = 0
            # format_nbc (byte 6): Number of channels minus 1, OR in service context: service type
            header[6] = VBAN_SERVICE_RTPACKETREGISTER  # 32
            # format_bit (byte 7): Bit depth (audio) OR timeout (service packets)
            header[7] = timeout & 0xFF

            # Stream name for registration - 16 bytes max
            if isinstance(stream_name, bytes):
                stream_bytes = stream_name[:16]
            else:
                stream_bytes = stream_name.encode("utf-8")[:16]
            header[8:8 + len(stream_bytes)] = stream_bytes

            # Frame counter
            header[24:28] = struct.pack("<I", self.frame_counter)
            self.frame_counter = (self.frame_counter + 1) % 0xFFFFFFFF

            # Send just the 28-byte header - no additional data
            packet = bytes(header)
            send_socket = source_socket or self.socket
            send_socket.sendto(packet, (self.ip, self.port))
            print(f"[VBAN] Sent RT-Packet registration (timeout={timeout}s)")
            return True
        except Exception as e:
            print(f"[VBAN] Error registering RT packet: {e}")
            return False


class VBANRTPacketListener:
    """Listen for VBAN RT-Packets containing level meters"""

    def __init__(self, port: int = 6990):
        self.port = port
        self.socket = None
        self.thread = None
        self.running = False
        self.lock = threading.Lock()
        self.voicemeeter_type = None

        # Level data - 34 inputs, 64 outputs (dB * 100)
        self.input_levels = [0] * 34
        self.output_levels = [0] * 64
        self.strip_states = [0] * 8
        self.bus_states = [0] * 8

    def start(self):
        """Start listening thread"""
        if self.running:
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', self.port))
            self.socket.settimeout(0.1)  # 100ms timeout for clean shutdown

            self.running = True
            self.thread = threading.Thread(target=self._listen_thread, daemon=True)
            self.thread.start()
            print(f"[RT-Listener] Started listening on port {self.port}")
            return True
        except Exception as e:
            print(f"[RT-Listener] Error starting: {e}")
            return False

    def stop(self):
        """Stop listening thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.socket:
            self.socket.close()

    def _listen_thread(self):
        """Background thread to receive RT packets"""
        packet_count = 0
        print("[RT-Listener] Thread started, waiting for packets...")

        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                packet_count += 1

                # Debug first packet received
                if packet_count == 1:
                    print(f"[RT-Listener] First packet received from {addr}, length={len(data)}")

                if len(data) >= 28:
                    # Check VBAN header
                    if data[0:4] == b"VBAN":
                        protocol = data[4] & 0xE0
                        service_type = data[6]

                        if protocol == VBAN_PROTOCOL_SERVICE and service_type == VBAN_SERVICE_RTPACKET:
                            if packet_count == 1:
                                print(f"[RT-Listener] First RT packet validated! Protocol={hex(protocol)}, Service={service_type}")
                            self._parse_rt_packet(data[28:])  # Skip 28-byte header
                        elif packet_count <= 3:
                            print(f"[RT-Listener] Packet {packet_count}: Wrong type - protocol={hex(protocol)}, service={service_type}")
                    elif packet_count <= 3:
                        print(f"[RT-Listener] Packet {packet_count}: Not VBAN - header={data[0:4]}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[RT-Listener] Error: {e}")

    def _parse_rt_packet(self, data):
        """Parse RT packet structure"""
        try:
            if len(data) < 212:  # Minimum size check for levels
                if not hasattr(self, '_warned_size'):
                    print(f"[RT-Listener] Warning: Packet too small ({len(data)} bytes, need 212+)")
                    self._warned_size = True
                return

            # Skip first 16 bytes (voicemeeterType, reserved, buffersize, version, optionBits, samplerate)
            vm_type = data[0]
            offset = 16

            # Extract input levels: 34 x short (2 bytes each) = 68 bytes
            input_levels = struct.unpack_from("<34h", data, offset)
            offset += 68

            # Extract output levels: 64 x short (2 bytes each) = 128 bytes
            output_levels = struct.unpack_from("<64h", data, offset)
            offset += 128

            strip_states = None
            bus_states = None
            if len(data) >= offset + 4 + 32 + 32:
                _ = struct.unpack_from("<I", data, offset)[0]
                offset += 4
                strip_states = struct.unpack_from("<8I", data, offset)
                offset += 32
                bus_states = struct.unpack_from("<8I", data, offset)

            # Update with lock
            with self.lock:
                self.voicemeeter_type = vm_type
                self.input_levels = [level * 0.01 for level in input_levels]  # Convert to dB
                self.output_levels = [level * 0.01 for level in output_levels]
                if strip_states is not None:
                    self.strip_states = list(strip_states)
                if bus_states is not None:
                    self.bus_states = list(bus_states)

            # Debug: Print first 5 input and output levels (once every 50 packets)
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
                print(f"[RT-Listener] First packet parsed successfully!")
            self._debug_counter += 1
            if self._debug_counter % 50 == 0:
                print(f"[RT-Listener] Input[0-4]: {[f'{l:.1f}dB' for l in self.input_levels[:5]]}")
                print(f"[RT-Listener] Output[0-4]: {[f'{l:.1f}dB' for l in self.output_levels[:5]]}")

        except Exception as e:
            print(f"Error parsing RT packet: {e}")

    def get_input_level(self, index: int) -> float:
        """Get input level in dB for given strip index"""
        with self.lock:
            base, count = self._strip_channel_range(index)
            return self._level_from_range(self.input_levels, base, count)
        return -100.0

    def get_output_level(self, index: int) -> float:
        """Get output level in dB for given bus index"""
        with self.lock:
            base, count = self._bus_channel_range(index)
            return self._level_from_range(self.output_levels, base, count)
        return -100.0

    def get_strip_state(self, index: int):
        with self.lock:
            if 0 <= index < len(self.strip_states):
                return self.strip_states[index]
        return None

    def get_bus_state(self, index: int):
        with self.lock:
            if 0 <= index < len(self.bus_states):
                return self.bus_states[index]
        return None

    def _strip_channel_range(self, index: int):
        vm_type = self.voicemeeter_type
        if vm_type == 1:
            if index < 2:
                return index * 2, 2
            return 4 + (index - 2) * 8, 8
        if vm_type == 2:
            if index < 3:
                return index * 2, 2
            return 6 + (index - 3) * 8, 8
        if vm_type in (3, 6):
            if index < 5:
                return index * 2, 2
            return 10 + (index - 5) * 8, 8
        return index * 2, 2

    def _bus_channel_range(self, index: int):
        return index * 8, 8

    @staticmethod
    def _level_from_range(levels, base, count):
        if base < 0 or base >= len(levels):
            return -100.0
        end = min(base + count, len(levels))
        if end <= base:
            return -100.0
        return max(levels[base:end])


class CustomSlider(tk.Canvas):
    """Custom vertical slider with circular handle showing dB value"""

    def __init__(self, parent, from_val=12, to_val=-60, height=200, on_change=None):
        super().__init__(parent, width=50, height=height, bg=BG_COLOR, highlightthickness=0)
        self.from_val = from_val
        self.to_val = to_val
        self.slider_height = height
        self.on_change = on_change
        self.value = 0
        self.input_blocked = False
        self.min_height = 120
        self.base_height = height

        # Track
        self.track_x = 25
        self.track_top = 20
        self.track_bottom = height - 20
        self.track_line = self.create_line(self.track_x, self.track_top, self.track_x, self.track_bottom,
                         fill="#555", width=4)

        # Handle
        self.handle_radius = 18
        handle_y = self._value_to_y(0)
        self.handle = self.create_oval(
            self.track_x - self.handle_radius,
            handle_y - self.handle_radius,
            self.track_x + self.handle_radius,
            handle_y + self.handle_radius,
            fill="#2196F3",
            outline="#64B5F6",
            width=2,
            stipple="gray50"
        )
        self.handle_text = self.create_text(
            self.track_x, handle_y,
            text="0",
            fill="white",
            font=("", 9, "bold")
        )

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Double-Button-1>", self._on_double_click)
        # Scroll wheel support
        self.bind("<MouseWheel>", self._on_scroll)  # Windows/macOS
        self.bind("<Button-4>", self._on_scroll_up)  # Linux scroll up
        self.bind("<Button-5>", self._on_scroll_down)  # Linux scroll down
        # Resize support
        self.bind("<Configure>", self._on_resize)

    def _value_to_y(self, value):
        range_val = self.from_val - self.to_val
        normalized = (self.from_val - value) / range_val
        return self.track_top + normalized * (self.track_bottom - self.track_top)

    def _y_to_value(self, y):
        y = max(self.track_top, min(self.track_bottom, y))
        normalized = (y - self.track_top) / (self.track_bottom - self.track_top)
        return round(self.from_val - normalized * (self.from_val - self.to_val))

    def _on_click(self, event):
        if not self.input_blocked:
            self._update_from_y(event.y)

    def _on_drag(self, event):
        if not self.input_blocked:
            self._update_from_y(event.y)

    def _on_double_click(self, event):
        self.set_value(0)
        if self.on_change:
            self.on_change(0)
        self.input_blocked = True
        self.after(300, self._unblock_input)

    def _unblock_input(self):
        self.input_blocked = False

    def _update_from_y(self, y):
        self.value = self._y_to_value(y)
        handle_y = self._value_to_y(self.value)

        self.coords(
            self.handle,
            self.track_x - self.handle_radius,
            handle_y - self.handle_radius,
            self.track_x + self.handle_radius,
            handle_y + self.handle_radius
        )
        self.coords(self.handle_text, self.track_x, handle_y)
        self.itemconfig(self.handle_text, text=str(self.value))

        if self.on_change:
            self.on_change(self.value)

    def set_value(self, value):
        """Set slider value programmatically"""
        self.value = value
        handle_y = self._value_to_y(value)
        self.coords(
            self.handle,
            self.track_x - self.handle_radius,
            handle_y - self.handle_radius,
            self.track_x + self.handle_radius,
            handle_y + self.handle_radius
        )
        self.coords(self.handle_text, self.track_x, handle_y)
        self.itemconfig(self.handle_text, text=str(value))

    def _on_scroll(self, event):
        # Windows/macOS: event.delta is positive for scroll up, negative for scroll down
        if not self.input_blocked:
            if event.delta > 0:
                self._adjust_value(1)
            else:
                self._adjust_value(-1)

    def _on_scroll_up(self, event):
        # Linux scroll up
        if not self.input_blocked:
            self._adjust_value(1)

    def _on_scroll_down(self, event):
        # Linux scroll down
        if not self.input_blocked:
            self._adjust_value(-1)

    def _adjust_value(self, direction):
        """Adjust value by step in given direction (up=increase dB, down=decrease dB)"""
        step = 2  # 2 dB per scroll step
        new_val = self.value + (direction * step)
        new_val = max(self.to_val, min(self.from_val, new_val))  # Clamp to range
        self.set_value(new_val)
        if self.on_change:
            self.on_change(new_val)

    def _on_resize(self, event):
        """Handle resize events"""
        new_height = event.height
        if new_height < self.min_height:
            return

        self.slider_height = new_height
        self.track_bottom = new_height - 20

        # Update track line
        self.coords(self.track_line, self.track_x, self.track_top, self.track_x, self.track_bottom)

        # Update handle position
        self.set_value(self.value)

    def resize(self, new_height, new_width=None):
        """Manually resize the slider"""
        if new_height < self.min_height:
            new_height = self.min_height

        # Calculate width proportionally if not specified
        if new_width is None:
            scale = new_height / self.base_height
            new_width = int(50 * scale)
            new_width = max(40, min(80, new_width))

        self.config(height=new_height, width=new_width)
        self.slider_height = new_height
        self.track_x = new_width // 2
        self.track_bottom = new_height - 20

        # Scale handle radius
        self.handle_radius = max(14, min(24, int(18 * (new_height / self.base_height))))

        self.coords(self.track_line, self.track_x, self.track_top, self.track_x, self.track_bottom)
        self.set_value(self.value)


class VUMeter(tk.Canvas):
    """Vertical VU meter showing audio levels"""

    def __init__(self, parent, width=8, height=150):
        super().__init__(parent, width=width, height=height, bg=BG_DARKER, highlightthickness=0)
        self.meter_width = width
        self.meter_height = height
        self.level_db = -60.0  # Current level in dB

        # Create meter bar (will be updated with level)
        self.meter_bar = self.create_rectangle(
            0, height,
            width, height,
            fill="#00ff00",
            outline=""
        )

        # Start update loop
        self._update_display()

    def set_level(self, db_value: float):
        """Set the meter level in dB (-60 to +12)"""
        self.level_db = max(-60.0, min(12.0, db_value))

    def _update_display(self):
        """Update the visual display"""
        # Map dB to height (logarithmic scale)
        # -60dB = 0%, 0dB = ~70%, +12dB = 100%
        if self.level_db <= -60:
            percent = 0
        else:
            # Simplified mapping: -60dB to 0dB is 0-70%, 0dB to +12dB is 70-100%
            if self.level_db <= 0:
                percent = ((self.level_db + 60) / 60) * 0.7
            else:
                percent = 0.7 + (self.level_db / 12) * 0.3

        bar_height = int(self.meter_height * percent)
        bar_y = self.meter_height - bar_height

        # Color based on level
        if self.level_db > 6:
            color = "#ff0000"  # Red - too hot
        elif self.level_db > 0:
            color = "#ffaa00"  # Orange - getting hot
        elif self.level_db > -20:
            color = "#00ff00"  # Green - good
        else:
            color = "#004400"  # Dark green - quiet

        self.coords(self.meter_bar, 0, bar_y, self.meter_width, self.meter_height)
        self.itemconfig(self.meter_bar, fill=color)

        # Schedule next update
        self.after(50, self._update_display)  # 20 FPS


class Knob(tk.Canvas):
    """Rotary knob control - drag up/down to change value, value shown in center"""

    def __init__(self, parent, label: str, from_val=0, to_val=10, on_change=None, color="#FF9800", size=50):
        super().__init__(parent, width=size, height=size + 12, bg=BG_COLOR, highlightthickness=0)
        self.from_val = from_val
        self.to_val = to_val
        self.on_change = on_change
        self.value = 0 if from_val <= 0 <= to_val else from_val
        self.size = size
        self.base_size = size
        self.color = color
        self.label_text = label
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_value = 0

        self._draw_knob()

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        # Scroll wheel support
        self.bind("<MouseWheel>", self._on_scroll)  # Windows/macOS
        self.bind("<Button-4>", self._on_scroll_up)  # Linux scroll up
        self.bind("<Button-5>", self._on_scroll_down)  # Linux scroll down

    def _draw_knob(self):
        """Draw or redraw the knob at current size"""
        self.delete("all")
        size = self.size
        center_x = size // 2
        center_y = size // 2

        # Label below knob
        self.label_item = self.create_text(center_x, size + 6, text=self.label_text, fill="#888", font=("", 7, "bold"))

        # Outer ring (dark)
        ring_radius = size // 2 - 4
        self.outer_ring = self.create_oval(
            center_x - ring_radius, center_y - ring_radius,
            center_x + ring_radius, center_y + ring_radius,
            fill="#333", outline="#555", width=2
        )

        # Inner circle with value
        inner_radius = ring_radius - 6
        self.inner = self.create_oval(
            center_x - inner_radius, center_y - inner_radius,
            center_x + inner_radius, center_y + inner_radius,
            fill="#222", outline=""
        )

        # Value text in center - scale font with size
        font_size = max(8, size // 5)
        self.value_text = self.create_text(
            center_x, center_y,
            text=str(self.value),
            fill=self.color,
            font=("", font_size, "bold")
        )

        # Indicator line (shows position)
        self.indicator = self.create_line(
            center_x, center_y - inner_radius + 2,
            center_x, center_y - ring_radius + 2,
            fill=self.color, width=3
        )
        self._update_indicator()

    def _on_click(self, event):
        self.dragging = True
        self.drag_start_y = event.y_root
        self.drag_start_value = self.value
        # Grab mouse so we get events even outside the widget
        self.grab_set()

    def _on_drag(self, event):
        if self.dragging:
            # Moving up increases value, moving down decreases
            delta = self.drag_start_y - event.y_root  # Use root coords
            range_val = self.to_val - self.from_val
            # Sensitivity: full drag of 100px = full range
            change = (delta / 100) * range_val
            new_val = self.drag_start_value + change
            new_val = max(self.from_val, min(self.to_val, new_val))
            self.value = round(new_val)
            self._update_display()
            if self.on_change:
                self.on_change(self.value)

    def _on_release(self, event):
        self.dragging = False
        # Release the mouse grab
        self.grab_release()

    def _on_scroll(self, event):
        # Windows/macOS: event.delta is positive for scroll up, negative for scroll down
        if event.delta > 0:
            self._adjust_value(1)
        else:
            self._adjust_value(-1)

    def _on_scroll_up(self, event):
        # Linux scroll up
        self._adjust_value(1)

    def _on_scroll_down(self, event):
        # Linux scroll down
        self._adjust_value(-1)

    def _adjust_value(self, direction):
        """Adjust value by one step in the given direction"""
        range_val = self.to_val - self.from_val
        # Step size: roughly 5% of range, minimum 1
        step = max(1, abs(range_val) // 20)
        new_val = self.value + (direction * step)
        new_val = max(self.from_val, min(self.to_val, new_val))
        self.value = round(new_val)
        self._update_display()
        if self.on_change:
            self.on_change(self.value)

    def _update_indicator(self):
        import math
        center_x = self.size // 2
        center_y = self.size // 2
        ring_radius = self.size // 2 - 4
        inner_radius = ring_radius - 6

        # Map value to angle (-135 to +135 degrees, 0 at top)
        range_val = self.to_val - self.from_val
        if range_val == 0:
            normalized = 0.5
        else:
            normalized = (self.value - self.from_val) / range_val
        angle = math.radians(-135 + normalized * 270)  # -135 to +135

        # Calculate indicator line endpoints
        inner_x = center_x + (inner_radius - 4) * math.sin(angle)
        inner_y = center_y - (inner_radius - 4) * math.cos(angle)
        outer_x = center_x + (ring_radius - 2) * math.sin(angle)
        outer_y = center_y - (ring_radius - 2) * math.cos(angle)

        self.coords(self.indicator, inner_x, inner_y, outer_x, outer_y)

    def _update_display(self):
        self.itemconfig(self.value_text, text=str(self.value))
        self._update_indicator()

    def set_value(self, value):
        self.value = value
        self._update_display()

    def resize(self, new_size):
        """Resize the knob"""
        if new_size < 30:
            new_size = 30
        self.size = new_size
        self.config(width=new_size, height=new_size + 12)
        self._draw_knob()


class RoutingButton(tk.Button):
    """Small routing button (A1, A2, B1, etc.)"""

    def __init__(self, parent, text, on_toggle, initially_on=False, width=3, color_on="#4CAF50"):
        self.is_on = initially_on
        self.on_toggle = on_toggle
        self.color_on = color_on
        self.color_on_active = self._lighten_color(color_on)
        super().__init__(
            parent,
            text=text,
            font=("", 8, "bold"),
            width=width,
            height=1,
            bd=0,
            bg=color_on if initially_on else "#444",
            fg="white",
            activebackground=self.color_on_active if initially_on else "#666",
            command=self._toggle
        )

    def _lighten_color(self, hex_color):
        """Lighten a hex color"""
        # Simple lightening - just return a lighter version
        if hex_color == "#4CAF50":
            return "#66BB6A"
        elif hex_color == "#FF9800":
            return "#FFB74D"
        elif hex_color == "#9C27B0":
            return "#BA68C8"
        return "#666"

    def _toggle(self):
        self.is_on = not self.is_on
        self._update_appearance()
        self.on_toggle(self.is_on)

    def set_state(self, is_on: bool):
        if self.is_on != is_on:
            self.is_on = is_on
            self._update_appearance()

    def _update_appearance(self):
        if self.is_on:
            self.config(bg=self.color_on, activebackground=self.color_on_active)
        else:
            self.config(bg="#444", activebackground="#666")


class ChannelStrip(tk.Frame):
    """A single channel strip with slider, routing buttons, and mute"""

    def __init__(self, parent, label: str, index: int, vban: VBANSender, is_strip=True,
                 initial_state: dict = None, show_gate=False, show_eq=False, rt_listener=None, routing_buses=None):
        super().__init__(parent, bg=BG_COLOR)
        self.index = index
        self.vban = vban
        self.is_strip = is_strip
        self.show_gate = show_gate
        self.show_eq = show_eq
        self.label_text = label
        self.rt_listener = rt_listener
        self.routing_buttons = {}

        state = initial_state or {}
        self.muted = state.get("muted", False)

        # Label
        self.label = tk.Label(self, text=label, font=("", 11, "bold"),
                              bg=BG_COLOR, fg="white")
        self.label.pack(pady=(5, 3))

        # Gate knob (for HW inputs)
        if show_gate:
            idx = self.index
            self.gate_knob = Knob(
                self, "GATE",
                from_val=0, to_val=10,
                on_change=lambda v, i=idx: vban.set_strip_gate(i, v),
                color="#FF9800",
                size=40
            )
            self.gate_knob.set_value(state.get("gate", 0))
            self.gate_knob.pack(pady=(0, 2))

        # EQ knobs (for virtual inputs) - Bass, Mid, Treble
        if show_eq:
            idx = self.index
            eq_frame = tk.Frame(self, bg=BG_COLOR)
            eq_frame.pack(pady=(0, 2))

            self.eq_bass = Knob(
                eq_frame, "BASS",
                from_val=-12, to_val=12,
                on_change=lambda v, i=idx: vban.set_strip_eq_bass(i, v),
                color="#e91e63",
                size=40
            )
            self.eq_bass.set_value(state.get("eq_bass", 0))
            self.eq_bass.pack(side=tk.LEFT, padx=1)

            self.eq_mid = Knob(
                eq_frame, "MID",
                from_val=-12, to_val=12,
                on_change=lambda v, i=idx: vban.set_strip_eq_mid(i, v),
                color="#9C27B0",
                size=40
            )
            self.eq_mid.set_value(state.get("eq_mid", 0))
            self.eq_mid.pack(side=tk.LEFT, padx=1)

            self.eq_treble = Knob(
                eq_frame, "TREBLE",
                from_val=-12, to_val=12,
                on_change=lambda v, i=idx: vban.set_strip_eq_treble(i, v),
                color="#3f51b5",
                size=40
            )
            self.eq_treble.set_value(state.get("eq_treble", 0))
            self.eq_treble.pack(side=tk.LEFT, padx=1)

        # Middle section
        middle = tk.Frame(self, bg=BG_COLOR)
        middle.pack(fill=tk.BOTH, expand=True)

        # VU Meter (if RT listener provided)
        self.meter = None
        if rt_listener:
            meter_height = 150 if (show_gate or show_eq) else 180
            self.meter = VUMeter(middle, width=8, height=meter_height)
            self.meter.pack(side=tk.LEFT, padx=(5, 2))

        # Slider
        self.slider = CustomSlider(
            middle,
            from_val=12,
            to_val=-60,
            height=150 if (show_gate or show_eq) else 180,
            on_change=self._on_gain_change
        )
        self.slider.pack(side=tk.LEFT, padx=5)

        initial_gain = state.get("gain", 0)
        self.slider.set_value(initial_gain)

        # Routing buttons (strips only)
        if is_strip and routing_buses:
            routing_frame = tk.Frame(middle, bg=BG_COLOR)
            routing_frame.pack(side=tk.LEFT, padx=(2, 5))

            idx = self.index
            for bus_key, label_text in routing_buses:
                state_key = bus_key.lower()
                default_on = (bus_key == "A1")
                btn = RoutingButton(
                    routing_frame,
                    label_text,
                    lambda on, i=idx, b=bus_key: vban.set_strip_bus(i, b, on),
                    state.get(state_key, default_on)
                )
                btn.pack(pady=1)
                self.routing_buttons[bus_key] = btn

        # Mute button
        self.mute_btn = tk.Button(
            self,
            text="MUTE",
            font=("", 9, "bold"),
            width=6,
            height=1,
            bd=0,
            bg="#d32f2f" if self.muted else "#444",
            fg="white",
            activebackground="#b71c1c" if self.muted else "#666",
            command=self._on_mute_click
        )
        self.mute_btn.pack(pady=(3, 5))
        # Start meter update loop after all widgets exist
        if self.meter:
            self._update_meter()

    def _on_gain_change(self, gain):
        if self.is_strip:
            self.vban.set_strip_gain(self.index, gain)
        else:
            self.vban.set_bus_gain(self.index, gain)

    def _on_mute_click(self):
        self.muted = not self.muted
        self._update_mute_appearance()
        if self.is_strip:
            self.vban.set_strip_mute(self.index, self.muted)
        else:
            self.vban.set_bus_mute(self.index, self.muted)

    def set_mute_state(self, muted: bool):
        if muted != self.muted:
            self.muted = muted
            self._update_mute_appearance()

    def _update_mute_appearance(self):
        if self.muted:
            self.mute_btn.config(bg="#d32f2f", activebackground="#b71c1c")
        else:
            self.mute_btn.config(bg="#444", activebackground="#666")

    def _sync_from_rt_state(self):
        if not self.rt_listener:
            return
        if not hasattr(self, "mute_btn"):
            return
        if self.is_strip:
            state = self.rt_listener.get_strip_state(self.index)
            if state is None:
                return
            self.set_mute_state(bool(state & VMRTSTATE_MODE_MUTE))
            for bus_key, btn in self.routing_buttons.items():
                bit = ROUTING_STATE_BITS.get(bus_key)
                if bit is not None:
                    btn.set_state(bool(state & bit))
        else:
            state = self.rt_listener.get_bus_state(self.index)
            if state is None:
                return
            self.set_mute_state(bool(state & VMRTSTATE_MODE_MUTE))

    def _update_meter(self):
        """Update VU meter with current level from RT listener"""
        if not self.winfo_exists():
            return
        if self.meter and self.rt_listener:
            self._sync_from_rt_state()
            if self.is_strip:
                level_db = self.rt_listener.get_input_level(self.index)
            else:
                level_db = self.rt_listener.get_output_level(self.index)
            self.meter.set_level(level_db)
        # Schedule next update
        if self.meter:
            self.after(50, self._update_meter)  # 20 FPS

    def get_state(self) -> dict:
        state = {
            "gain": self.slider.value,
            "muted": self.muted
        }
        if self.is_strip:
            for bus_key, btn in self.routing_buttons.items():
                state[bus_key.lower()] = btn.is_on
        if self.show_gate:
            state["gate"] = self.gate_knob.value
        if self.show_eq:
            state["eq_bass"] = self.eq_bass.value
            state["eq_mid"] = self.eq_mid.value
            state["eq_treble"] = self.eq_treble.value
        return state

    def scale(self, scale_factor):
        """Scale the channel strip components"""
        # Scale slider height
        base_slider_height = 150 if (self.show_gate or self.show_eq) else 180
        new_height = int(base_slider_height * scale_factor)
        self.slider.resize(new_height)

        # Scale knobs
        base_knob_size = 40
        new_knob_size = int(base_knob_size * scale_factor)

        if self.show_gate:
            self.gate_knob.resize(new_knob_size)

        if self.show_eq:
            self.eq_bass.resize(new_knob_size)
            self.eq_mid.resize(new_knob_size)
            self.eq_treble.resize(new_knob_size)


class TapeRecorder(tk.Frame):
    """Tape recorder control panel matching Voicemeeter layout: <<, >>, |>, [], O"""

    def __init__(self, parent, vban: VBANSender):
        super().__init__(parent, bg=BG_COLOR)
        self.vban = vban

        btn_size = 28  # Fixed pixel size for all buttons

        def make_btn(text, command, fg="white"):
            frame = tk.Frame(self, width=btn_size, height=btn_size, bg="#444")
            frame.pack_propagate(False)
            frame.pack(side=tk.LEFT, padx=1)
            btn = tk.Button(
                frame, text=text, font=("", 8),
                bd=1, bg="#444", fg=fg, activebackground="#555",
                relief=tk.RAISED, command=command
            )
            btn.pack(expand=True, fill=tk.BOTH)
            return btn

        # Rewind <<
        self.rewind_btn = make_btn("<<", vban.recorder_rewind)
        # Fast Forward >>
        self.ff_btn = make_btn(">>", vban.recorder_forward)
        # Play |>
        self.play_btn = make_btn("▶", vban.recorder_play)
        # Stop []
        self.stop_btn = make_btn("■", vban.recorder_stop)
        # Record O (red)
        self.record_btn = make_btn("●", vban.recorder_record, fg="#d32f2f")


class SettingsDialog(tk.Toplevel):
    """Settings dialog"""

    def __init__(self, parent, config, on_save):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Settings")
        self.geometry("400x310")
        self.resizable(False, False)
        self.configure(bg=BG_COLOR)

        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="PC IP Address:", font=("", 12),
                 bg=BG_COLOR, fg="white").pack(pady=(20, 5))
        self.ip_entry = tk.Entry(self, font=("", 14), width=20)
        self.ip_entry.insert(0, config["pc_ip"])
        self.ip_entry.pack()

        tk.Label(self, text="VBAN Command Port:", font=("", 12),
                 bg=BG_COLOR, fg="white").pack(pady=(10, 5))
        self.port_entry = tk.Entry(self, font=("", 14), width=20)
        self.port_entry.insert(0, str(config["port"]))
        self.port_entry.pack()

        tk.Label(self, text="Stream Name:", font=("", 12),
                 bg=BG_COLOR, fg="white").pack(pady=(10, 5))
        self.stream_entry = tk.Entry(self, font=("", 14), width=20)
        self.stream_entry.insert(0, config["stream_name"])
        self.stream_entry.pack()

        tk.Label(self, text="Mixer Type:", font=("", 12),
                 bg=BG_COLOR, fg="white").pack(pady=(10, 5))
        self.mixer_var = tk.StringVar(value=config.get("mixer_type", "banana"))
        self.mixer_combo = ttk.Combobox(
            self,
            textvariable=self.mixer_var,
            values=["auto", "standard", "banana", "potato"],
            state="readonly",
            width=18
        )
        self.mixer_combo.pack()

        tk.Button(
            self,
            text="Save",
            font=("", 12, "bold"),
            width=15,
            height=1,
            bg="#4CAF50",
            fg="white",
            bd=0,
            command=self._save
        ).pack(pady=15)

    def _save(self):
        config = {
            "pc_ip": self.ip_entry.get(),
            "port": int(self.port_entry.get()),
            "stream_name": self.stream_entry.get(),
            "mixer_type": self.mixer_var.get()
        }
        self.on_save(config)
        self.destroy()


class VoicemeeterDeckApp:
    """Main application"""

    BASE_WIDTH = 1050
    BASE_HEIGHT = 450

    def __init__(self):
        self.config = self._load_config()
        self.mixer_type_setting = self.config.get("mixer_type", "auto")
        self.active_mixer_type = self._resolve_mixer_type(self.mixer_type_setting)
        self.mixer_profile = MIXER_PROFILES[self.active_mixer_type]
        self.base_width, self.base_height = self._calculate_base_size(self.mixer_profile)
        self.vban = VBANSender(
            self.config["pc_ip"],
            self.config["port"],
            self.config["stream_name"]
        )

        # RT Packet Listener for level meters
        self.rt_listener = VBANRTPacketListener(port=6990)
        self.rt_listener.start()

        # Create main window (need this before starting periodic tasks)
        self.root = tk.Tk()
        self.root.report_callback_exception = self._report_callback_exception
        self.root.title("VM Remote")
        self.root.geometry(f"{self.base_width}x{self.base_height}")
        self.root.minsize(800, 350)  # Minimum window size
        self.root.configure(bg=BG_COLOR)

        # Track last size for resize handling
        self.last_width = self.base_width
        self.last_height = self.base_height
        self.resize_after_id = None

        # Set window icon
        self._set_window_icon()

        self._create_ui()

        if self.mixer_type_setting == "auto":
            self._auto_detect_mixer_type()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Bind resize event
        self.root.bind("<Configure>", self._on_window_configure)

    def _set_window_icon(self):
        """Set the window/taskbar icon"""
        icon_path = Path(__file__).parent / "icon.png"

        # Set WM_CLASS for Linux taskbar icon matching
        # This must be done before the window is mapped
        try:
            self.root.wm_iconname("VM Remote")
            # Set the class for window managers to match with .desktop file
            self.root.tk.call('tk', 'appname', 'voicemeeter-deck')
        except Exception:
            pass

        if icon_path.exists():
            if HAS_PIL:
                try:
                    img = Image.open(icon_path)
                    # Create multiple sizes for better taskbar display
                    self.icon_images = []
                    # Support both old and new Pillow API
                    resample = getattr(Image, 'LANCZOS', None) or getattr(Image.Resampling, 'LANCZOS', Image.BICUBIC)
                    for size in [16, 32, 48, 64, 128, 256]:
                        resized = img.resize((size, size), resample)
                        self.icon_images.append(ImageTk.PhotoImage(resized))

                    # Set all icon sizes
                    self.root.iconphoto(True, *self.icon_images)
                    return
                except Exception as e:
                    print(f"Error loading icon: {e}")

            try:
                self.icon_images = [tk.PhotoImage(file=str(icon_path))]
                self.root.iconphoto(True, *self.icon_images)
            except Exception as e:
                print(f"Error loading icon without PIL: {e}")

    def _load_config(self) -> dict:
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE) as f:
                    loaded = json.load(f)
                    config = DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
        except Exception as e:
            print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

    def _report_callback_exception(self, exc, val, tb):
        _log_exception(exc, val, tb)

    def _save_config(self, config: dict):
        try:
            previous_type = self.mixer_type_setting
            config["strips"] = self.config.get("strips", {})
            config["buses"] = self.config.get("buses", {})

            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            self.config = config
            self.vban = VBANSender(
                config["pc_ip"],
                config["port"],
                config["stream_name"]
            )
            self.mixer_type_setting = config.get("mixer_type", "auto")
            if self.mixer_type_setting != previous_type:
                if self.mixer_type_setting == "auto":
                    self._auto_detect_mixer_type()
                else:
                    self._apply_mixer_type(self.mixer_type_setting)
            self._update_status_label()
            messagebox.showinfo("Settings", "Settings saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def _resolve_mixer_type(self, mixer_type: str) -> str:
        if mixer_type == "auto":
            detected = self._detect_mixer_type()
            if detected:
                return detected
            return "banana"
        return mixer_type if mixer_type in MIXER_PROFILES else "banana"

    def _detect_mixer_type(self):
        listener = getattr(self, "rt_listener", None)
        vm_type = listener.voicemeeter_type if listener else None
        return VM_TYPE_TO_PROFILE.get(vm_type)

    def _auto_detect_mixer_type(self):
        detected = self._detect_mixer_type()
        if detected:
            if detected != self.active_mixer_type:
                self._apply_mixer_type(detected)
            return
        self.root.after(500, self._auto_detect_mixer_type)

    def _apply_mixer_type(self, mixer_type: str):
        if mixer_type not in MIXER_PROFILES:
            return
        if mixer_type == self.active_mixer_type:
            return
        self.active_mixer_type = mixer_type
        self.mixer_profile = MIXER_PROFILES[self.active_mixer_type]
        self.base_width, self.base_height = self._calculate_base_size(self.mixer_profile)
        self.last_width = self.base_width
        self.last_height = self.base_height
        self.root.geometry(f"{self.base_width}x{self.base_height}")
        if hasattr(self, "content"):
            self._clear_mixer_frames()
            self._build_mixer_frames()
        self._update_status_label()

    def _calculate_base_size(self, profile: dict):
        total_columns = len(profile["strip_labels"]) + len(profile["bus_labels"])
        base_width = max(800, 200 + (total_columns * 85))
        return base_width, self.BASE_HEIGHT

    def _update_status_label(self):
        if not hasattr(self, "status"):
            return
        mixer_label = self.active_mixer_type
        if self.mixer_type_setting == "auto":
            mixer_label = f"auto -> {self.active_mixer_type}"
        self.status.config(text=f"Connected to {self.config['pc_ip']}:{self.config['port']} ({mixer_label})")

    def _create_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG_COLOR)
        header.pack(fill=tk.X, padx=20, pady=4)

        # Logo - try to load PNG, fall back to text
        self.logo_image = None
        logo_path = Path(__file__).parent / "logo.png"
        logo_label = None

        def _scaled_logo_size(original_width: int, original_height: int):
            target_width = max(1, int(original_width * LOGO_SCALE))
            target_height = max(1, int(original_height * LOGO_SCALE))
            base_height = getattr(self, "base_height", self.BASE_HEIGHT)
            max_height = int(base_height * LOGO_MAX_HEIGHT_RATIO)
            if max_height > 0 and target_height > max_height:
                ratio = max_height / float(target_height)
                target_width = max(1, int(target_width * ratio))
                target_height = max_height
            return target_width, target_height

        if logo_path.exists() and HAS_PIL:
            try:
                img = Image.open(logo_path)
                target_width, target_height = _scaled_logo_size(img.width, img.height)
                # Support both old and new Pillow API
                resample = getattr(Image, 'LANCZOS', None) or getattr(Image.Resampling, 'LANCZOS', Image.BICUBIC)
                img = img.resize((target_width, target_height), resample)
                self.logo_image = ImageTk.PhotoImage(img)
                logo_label = tk.Label(header, image=self.logo_image, bg=BG_COLOR)
                logo_label.pack(side=tk.LEFT)
            except Exception as e:
                print(f"Error loading logo: {e}")

        if logo_label is None and logo_path.exists():
            try:
                self.logo_image = tk.PhotoImage(file=str(logo_path))
                width = self.logo_image.width()
                height = self.logo_image.height()
                target_width, target_height = _scaled_logo_size(width, height)
                if width < target_width or height < target_height:
                    import math
                    zoom = max(1, math.ceil(target_width / width), math.ceil(target_height / height))
                    if zoom > 1:
                        self.logo_image = self.logo_image.zoom(zoom, zoom)
                        width = self.logo_image.width()
                        height = self.logo_image.height()
                if width > target_width or height > target_height:
                    import math
                    scale = max(math.ceil(width / target_width), math.ceil(height / target_height))
                    if scale > 1:
                        self.logo_image = self.logo_image.subsample(scale, scale)
                logo_label = tk.Label(header, image=self.logo_image, bg=BG_COLOR)
                logo_label.pack(side=tk.LEFT)
            except Exception as e:
                print(f"Error loading logo without PIL: {e}")

        if logo_label is None:
            title = tk.Label(header, text="VM Remote", font=("", 18, "bold"),
                             bg=BG_COLOR, fg="white")
            title.pack(side=tk.LEFT)

        # Settings button (far right)
        settings_btn = tk.Button(
            header,
            text="Settings",
            font=("", 11),
            bg="#333",
            fg="white",
            bd=0,
            command=self._open_settings
        )
        settings_btn.pack(side=tk.RIGHT)

        # Tape recorder controls (right of title)
        self.recorder = TapeRecorder(header, self.vban)
        self.recorder.pack(side=tk.RIGHT, padx=20)

        # Content
        self.content = tk.Frame(self.root, bg=BG_COLOR)
        self.content.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self._build_mixer_frames()

        # Status
        self.status = tk.Label(
            self.root,
            text="",
            font=("", 9),
            bg=BG_COLOR,
            fg="#888"
        )
        self.status.pack(pady=5)
        self._update_status_label()

    def _clear_mixer_frames(self):
        if hasattr(self, "strips_frame") and self.strips_frame:
            self.strips_frame.destroy()
        if hasattr(self, "buses_frame") and self.buses_frame:
            self.buses_frame.destroy()
        self.strips = []
        self.buses = []

    def _build_mixer_frames(self):
        profile = self.mixer_profile
        strip_labels = profile["strip_labels"]
        routing_buses = profile["routing_buses"]
        hardware_strips = profile["hardware_strips"]

        self.strips_frame = tk.LabelFrame(self.content, text=" Inputs ", font=("", 10),
                                          bg=BG_COLOR, fg="white", bd=1)
        self.strips_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        strips_inner = tk.Frame(self.strips_frame, bg=BG_COLOR)
        strips_inner.pack(pady=5)

        self.strips = []
        for i, label in enumerate(strip_labels):
            strip_state = self.config.get("strips", {}).get(str(i), None)
            # HW strips get Gate, virtual strips get EQ
            show_gate = (i < hardware_strips)
            show_eq = (i >= hardware_strips)
            strip = ChannelStrip(strips_inner, label, i, self.vban, is_strip=True,
                                 initial_state=strip_state, show_gate=show_gate, show_eq=show_eq,
                                 rt_listener=self.rt_listener, routing_buses=routing_buses)
            strip.pack(side=tk.LEFT, padx=3)
            self.strips.append(strip)

        self.buses_frame = tk.LabelFrame(self.content, text=" Outputs ", font=("", 10),
                                         bg=BG_COLOR, fg="white", bd=1)
        self.buses_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        buses_inner = tk.Frame(self.buses_frame, bg=BG_COLOR)
        buses_inner.pack(pady=5)

        bus_labels = profile["bus_labels"]
        self.buses = []
        for i, label in enumerate(bus_labels):
            bus_state = self.config.get("buses", {}).get(str(i), None)
            bus = ChannelStrip(buses_inner, label, i, self.vban, is_strip=False,
                               initial_state=bus_state, rt_listener=self.rt_listener)
            bus.pack(side=tk.LEFT, padx=3)
            self.buses.append(bus)

    def _save_channel_states(self):
        strips = {}
        for i, strip in enumerate(self.strips):
            strips[str(i)] = strip.get_state()

        buses = {}
        for i, bus in enumerate(self.buses):
            buses[str(i)] = bus.get_state()

        self.config["strips"] = strips
        self.config["buses"] = buses

        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _on_close(self):
        self._save_channel_states()
        self.rt_listener.stop()
        self.root.destroy()

    def _open_settings(self):
        SettingsDialog(self.root, self.config, self._save_config)

    def _on_window_configure(self, event):
        """Handle window resize events"""
        # Only respond to root window changes
        if event.widget != self.root:
            return

        new_width = event.width
        new_height = event.height

        # Check if size actually changed significantly
        if abs(new_width - self.last_width) < 10 and abs(new_height - self.last_height) < 10:
            return

        self.last_width = new_width
        self.last_height = new_height

        # Debounce resize events - cancel previous scheduled resize
        if self.resize_after_id:
            self.root.after_cancel(self.resize_after_id)

        # Schedule the actual resize after a short delay
        self.resize_after_id = self.root.after(100, self._do_resize)

    def _do_resize(self):
        """Actually perform the resize scaling"""
        self.resize_after_id = None

        # Calculate scale factor based on height (primary constraint for mixer UI)
        height_scale = self.last_height / self.base_height
        width_scale = self.last_width / self.base_width

        # Use the smaller scale factor to ensure everything fits
        scale_factor = min(height_scale, width_scale)

        # Clamp scale factor to reasonable bounds
        scale_factor = max(0.7, min(2.0, scale_factor))

        # Scale all channel strips
        for strip in self.strips:
            strip.scale(scale_factor)

        for bus in self.buses:
            bus.scale(scale_factor)

    def _periodic_rt_registration(self):
        """Re-register for RT packets every 10 seconds (as per SDK sample)"""
        try:
            self.vban.register_rt_packet(timeout=15, source_socket=self.rt_listener.socket)
        except Exception as e:
            print(f"Error in periodic RT registration: {e}")
        # Schedule next registration in 10 seconds (10000ms)
        self.root.after(10000, self._periodic_rt_registration)

    def run(self):
        # Start periodic RT packet registration
        self._periodic_rt_registration()
        self.root.mainloop()


if __name__ == "__main__":
    app = VoicemeeterDeckApp()
    app.run()
