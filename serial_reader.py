import os
import re
import time

import serial
from serial.tools import list_ports

FRAME_RE = re.compile(r'^\[(\d+),(\d+)\]$')


def parse_frame(line):
    """
    Parse a raw '[ID,distance]' line into (sensor_id, distance_cm).
    Returns None if the line is malformed or out of the HC-SR04's valid range.
    """
    match = FRAME_RE.match(line.strip())
    if not match:
        return None
    sensor_id, distance = int(match.group(1)), int(match.group(2))
    if not (1 <= sensor_id <= 4 and 2 <= distance <= 400):
        return None
    return sensor_id, distance


class SerialReader:
    """Owns one Arduino's USB serial port and hands parsed readings to a callback."""

    def __init__(self, port, baud, on_reading):
        self.port = port
        self.baud = baud
        self.on_reading = on_reading
        self._ser = None
        self.connected = False
        self._running = False

    def connect(self):
        self._ser = serial.Serial(self.port, self.baud, timeout=1)
        self.connected = True

    def run(self):
        """Blocking read loop — call from a background thread."""
        self._running = True
        while self._running:
            try:
                raw = self._ser.readline().decode('utf-8', errors='ignore')
                if not raw:
                    continue
                parsed = parse_frame(raw)
                if parsed:
                    sensor_id, distance = parsed
                    self.on_reading(sensor_id, distance, time.time())
            except (serial.SerialException, OSError):
                self.connected = False
                break

    def stop(self):
        self._running = False
        if self._ser:
            self._ser.close()


def _resolve_by_path_map(by_path_dir):
    """Maps a device path (e.g. '/dev/ttyUSB0') to its stable by-path symlink,
    for every symlink found in by_path_dir. Empty dict if the dir doesn't exist
    (non-Linux dev machines, or a Pi without /dev/serial/by-path populated)."""
    if not os.path.isdir(by_path_dir):
        return {}
    mapping = {}
    for name in os.listdir(by_path_dir):
        full = os.path.join(by_path_dir, name)
        try:
            mapping[os.path.realpath(full)] = full
        except OSError:
            continue
    return mapping


def list_available_ports(comports_fn=list_ports.comports, by_path_dir='/dev/serial/by-path'):
    """
    Returns every connected serial port as {'port_id': str, 'device': str}.
    port_id is the physical-USB-port-based /dev/serial/by-path id when available
    (stable across reboots, unlike USB serial numbers on cheap CH340 clones which
    are often duplicated) — falls back to the raw device path otherwise.
    """
    by_path_map = _resolve_by_path_map(by_path_dir)
    return [
        {'port_id': by_path_map.get(p.device, p.device), 'device': p.device}
        for p in comports_fn()
    ]
