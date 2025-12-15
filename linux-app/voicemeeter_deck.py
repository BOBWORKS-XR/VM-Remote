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
from pathlib import Path

# Try to import PIL for logo support
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# VBAN Protocol Constants
VBAN_PROTOCOL_TXT = 0x40
VBAN_DATA_FORMAT = 0x10

# UI Colors - dark gray theme
BG_COLOR = "#2d2d2d"  # Main background - lighter black/dark gray
BG_DARKER = "#252525"  # Slightly darker for contrast

CONFIG_FILE = Path.home() / ".config" / "voicemeeter-deck" / "config.json"

DEFAULT_CONFIG = {
    "pc_ip": "192.168.1.212",
    "port": 6980,
    "stream_name": "Command1",
    "strips": {},
    "buses": {},
    "recorder": {"play": False, "record": False, "pause": False}
}


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

    def set_strip_a1(self, index: int, enabled: bool):
        self.send_command(f"Strip[{index}].A1={1 if enabled else 0};")

    def set_strip_a2(self, index: int, enabled: bool):
        self.send_command(f"Strip[{index}].A2={1 if enabled else 0};")

    def set_strip_a3(self, index: int, enabled: bool):
        self.send_command(f"Strip[{index}].A3={1 if enabled else 0};")

    def set_strip_b1(self, index: int, enabled: bool):
        self.send_command(f"Strip[{index}].B1={1 if enabled else 0};")

    def set_strip_b2(self, index: int, enabled: bool):
        self.send_command(f"Strip[{index}].B2={1 if enabled else 0};")

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

        # Track
        self.track_x = 25
        self.track_top = 20
        self.track_bottom = height - 20
        self.create_line(self.track_x, self.track_top, self.track_x, self.track_bottom,
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


class Knob(tk.Canvas):
    """Rotary knob control - drag up/down to change value, value shown in center"""

    def __init__(self, parent, label: str, from_val=0, to_val=10, on_change=None, color="#FF9800", size=50):
        super().__init__(parent, width=size, height=size + 12, bg=BG_COLOR, highlightthickness=0)
        self.from_val = from_val
        self.to_val = to_val
        self.on_change = on_change
        self.value = 0 if from_val <= 0 <= to_val else from_val
        self.size = size
        self.color = color
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_value = 0

        center_x = size // 2
        center_y = size // 2

        # Label above knob
        self.create_text(center_x, size + 6, text=label, fill="#888", font=("", 7, "bold"))

        # Outer ring (dark)
        ring_radius = size // 2 - 4
        self.create_oval(
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

        # Value text in center
        self.value_text = self.create_text(
            center_x, center_y,
            text=str(self.value),
            fill=color,
            font=("", 10, "bold")
        )

        # Indicator line (shows position)
        self.indicator = self.create_line(
            center_x, center_y - inner_radius + 2,
            center_x, center_y - ring_radius + 2,
            fill=color, width=3
        )
        self._update_indicator()

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        # Scroll wheel support
        self.bind("<MouseWheel>", self._on_scroll)  # Windows/macOS
        self.bind("<Button-4>", self._on_scroll_up)  # Linux scroll up
        self.bind("<Button-5>", self._on_scroll_down)  # Linux scroll down

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

    def _update_appearance(self):
        if self.is_on:
            self.config(bg=self.color_on, activebackground=self.color_on_active)
        else:
            self.config(bg="#444", activebackground="#666")


class ChannelStrip(tk.Frame):
    """A single channel strip with slider, routing buttons, and mute"""

    def __init__(self, parent, label: str, index: int, vban: VBANSender, is_strip=True,
                 initial_state: dict = None, show_gate=False, show_eq=False):
        super().__init__(parent, bg=BG_COLOR)
        self.index = index
        self.vban = vban
        self.is_strip = is_strip
        self.show_gate = show_gate
        self.show_eq = show_eq

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
        if is_strip:
            routing_frame = tk.Frame(middle, bg=BG_COLOR)
            routing_frame.pack(side=tk.LEFT, padx=(2, 5))

            idx = self.index

            self.a1_btn = RoutingButton(routing_frame, "A1",
                                        lambda on, i=idx: vban.set_strip_a1(i, on),
                                        state.get("a1", True))
            self.a1_btn.pack(pady=1)

            self.a2_btn = RoutingButton(routing_frame, "A2",
                                        lambda on, i=idx: vban.set_strip_a2(i, on),
                                        state.get("a2", False))
            self.a2_btn.pack(pady=1)

            self.a3_btn = RoutingButton(routing_frame, "A3",
                                        lambda on, i=idx: vban.set_strip_a3(i, on),
                                        state.get("a3", False))
            self.a3_btn.pack(pady=1)

            self.b1_btn = RoutingButton(routing_frame, "B1",
                                        lambda on, i=idx: vban.set_strip_b1(i, on),
                                        state.get("b1", False))
            self.b1_btn.pack(pady=1)

            self.b2_btn = RoutingButton(routing_frame, "B2",
                                        lambda on, i=idx: vban.set_strip_b2(i, on),
                                        state.get("b2", False))
            self.b2_btn.pack(pady=1)

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

    def _update_mute_appearance(self):
        if self.muted:
            self.mute_btn.config(bg="#d32f2f", activebackground="#b71c1c")
        else:
            self.mute_btn.config(bg="#444", activebackground="#666")

    def get_state(self) -> dict:
        state = {
            "gain": self.slider.value,
            "muted": self.muted
        }
        if self.is_strip:
            state["a1"] = self.a1_btn.is_on
            state["a2"] = self.a2_btn.is_on
            state["a3"] = self.a3_btn.is_on
            state["b1"] = self.b1_btn.is_on
            state["b2"] = self.b2_btn.is_on
        if self.show_gate:
            state["gate"] = self.gate_knob.value
        if self.show_eq:
            state["eq_bass"] = self.eq_bass.value
            state["eq_mid"] = self.eq_mid.value
            state["eq_treble"] = self.eq_treble.value
        return state


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
        self.geometry("400x250")
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
            "stream_name": self.stream_entry.get()
        }
        self.on_save(config)
        self.destroy()


class VoicemeeterDeckApp:
    """Main application"""

    def __init__(self):
        self.config = self._load_config()
        self.vban = VBANSender(
            self.config["pc_ip"],
            self.config["port"],
            self.config["stream_name"]
        )

        # Create main window
        self.root = tk.Tk()
        self.root.title("VM Remote")
        self.root.geometry("1050x450")
        self.root.minsize(950, 400)  # Minimum window size
        self.root.configure(bg=BG_COLOR)

        # Set window icon
        self._set_window_icon()

        self._create_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_window_icon(self):
        """Set the window/taskbar icon"""
        icon_path = Path(__file__).parent / "icon.png"
        if HAS_PIL and icon_path.exists():
            try:
                img = Image.open(icon_path)
                self.icon_image = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self.icon_image)
            except Exception as e:
                print(f"Error loading icon: {e}")

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

    def _save_config(self, config: dict):
        try:
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
            messagebox.showinfo("Settings", "Settings saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def _create_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG_COLOR)
        header.pack(fill=tk.X, padx=20, pady=10)

        # Logo - try to load PNG, fall back to text
        self.logo_image = None
        logo_path = Path(__file__).parent / "logo.png"
        if HAS_PIL and logo_path.exists():
            try:
                img = Image.open(logo_path)
                img = img.resize((150, 48), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
                logo_label = tk.Label(header, image=self.logo_image, bg=BG_COLOR)
                logo_label.pack(side=tk.LEFT)
            except Exception as e:
                print(f"Error loading logo: {e}")
                title = tk.Label(header, text="VM Remote", font=("", 18, "bold"),
                                 bg=BG_COLOR, fg="white")
                title.pack(side=tk.LEFT)
        else:
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
        content = tk.Frame(self.root, bg=BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Strips
        strips_frame = tk.LabelFrame(content, text=" Inputs ", font=("", 10),
                                     bg=BG_COLOR, fg="white", bd=1)
        strips_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        strips_inner = tk.Frame(strips_frame, bg=BG_COLOR)
        strips_inner.pack(pady=5)

        strip_labels = ["HW 1", "HW 2", "HW 3", "Virt 1", "Virt 2"]
        self.strips = []
        for i, label in enumerate(strip_labels):
            strip_state = self.config.get("strips", {}).get(str(i), None)
            # HW 1-3 (index 0-2) get Gate, Virt 1-2 (index 3-4) get EQ
            show_gate = (i < 3)
            show_eq = (i >= 3)
            strip = ChannelStrip(strips_inner, label, i, self.vban, is_strip=True,
                                 initial_state=strip_state, show_gate=show_gate, show_eq=show_eq)
            strip.pack(side=tk.LEFT, padx=3)
            self.strips.append(strip)

        # Buses
        buses_frame = tk.LabelFrame(content, text=" Outputs ", font=("", 10),
                                    bg=BG_COLOR, fg="white", bd=1)
        buses_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        buses_inner = tk.Frame(buses_frame, bg=BG_COLOR)
        buses_inner.pack(pady=5)

        bus_labels = ["A1", "A2", "A3", "B1", "B2"]
        self.buses = []
        for i, label in enumerate(bus_labels):
            bus_state = self.config.get("buses", {}).get(str(i), None)
            bus = ChannelStrip(buses_inner, label, i, self.vban, is_strip=False,
                               initial_state=bus_state)
            bus.pack(side=tk.LEFT, padx=3)
            self.buses.append(bus)

        # Status
        self.status = tk.Label(
            self.root,
            text=f"Connected to {self.config['pc_ip']}:{self.config['port']}",
            font=("", 9),
            bg=BG_COLOR,
            fg="#888"
        )
        self.status.pack(pady=5)

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
        self.root.destroy()

    def _open_settings(self):
        SettingsDialog(self.root, self.config, self._save_config)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = VoicemeeterDeckApp()
    app.run()
