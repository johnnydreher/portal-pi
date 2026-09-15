import re
import time

import serial

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
