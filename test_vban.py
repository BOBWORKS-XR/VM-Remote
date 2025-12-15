"""
Test VBAN text command directly from Windows
Run this on your PC to test if VBAN commands work
"""

import socket
import struct

# VBAN Protocol Constants
VBAN_PROTOCOL_TXT = 0x40
VBAN_DATA_FORMAT = 0x10

def send_vban_command(ip: str, port: int, stream_name: str, command: str):
    """Send a VBAN text command"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Build header (28 bytes)
    header = bytearray(28)
    header[0:4] = b"VBAN"
    header[4] = VBAN_PROTOCOL_TXT  # 0x40
    header[5] = 0  # nbs
    header[6] = 0  # nbc
    header[7] = VBAN_DATA_FORMAT  # 0x10
    stream_bytes = stream_name.encode("utf-8")[:16]
    header[8:8 + len(stream_bytes)] = stream_bytes
    header[24:28] = struct.pack("<I", 0)  # frame counter

    # Build packet
    text_bytes = command.encode("utf-8")
    packet = bytes(header) + text_bytes

    print(f"Sending to {ip}:{port}")
    print(f"Stream: {stream_name}")
    print(f"Command: {command}")
    print(f"Header bytes: {header.hex()}")
    print(f"Packet size: {len(packet)} bytes")

    sock.sendto(packet, (ip, port))
    sock.close()
    print("Sent!")

if __name__ == "__main__":
    # Test with your settings
    IP = "192.168.1.212"  # Your PC IP (localhost since running on same PC)
    PORT = 6980
    STREAM = "Command1"

    # Try muting Strip 0
    send_vban_command(IP, PORT, STREAM, "Strip[0].Mute=1;")

    input("Press Enter to unmute...")
    send_vban_command(IP, PORT, STREAM, "Strip[0].Mute=0;")
