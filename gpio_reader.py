import time

from distance import pulse_duration_to_cm

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

TRIGGER_PULSE_S = 0.00001  # 10 microseconds, per HC-SR04 datasheet
TIMEOUT_S = 0.03  # generous timeout for the sensor's 400cm max range


class GpioSensor:
    """Drives one HC-SR04 sensor's TRIG/ECHO pins directly on the Pi's GPIO."""

    def __init__(self, trigger_pin, echo_pin):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO is not available — this must run on a Raspberry Pi")
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trigger_pin, GPIO.LOW)

    def measure_distance_cm(self):
        """Returns the measured distance in cm, or None if the echo pulse timed out."""
        GPIO.output(self.trigger_pin, GPIO.HIGH)
        time.sleep(TRIGGER_PULSE_S)
        GPIO.output(self.trigger_pin, GPIO.LOW)

        deadline = time.time() + TIMEOUT_S
        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()
            if pulse_start > deadline:
                return None

        deadline = time.time() + TIMEOUT_S
        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()
            if pulse_end > deadline:
                return None

        return pulse_duration_to_cm(pulse_end - pulse_start)


class GpioReader:
    """Cycles through all 4 HC-SR04 sensors, calling on_reading for each successful measurement."""

    def __init__(self, sensors, on_reading, poll_interval_s=0.01):
        """sensors: dict[str, GpioSensor] keyed by gate name."""
        self.sensors = sensors
        self.on_reading = on_reading
        self.poll_interval_s = poll_interval_s
        self.connected = False
        self._running = False

    def connect(self):
        self.connected = True

    def run(self):
        """Blocking read loop — call from a background thread."""
        self._running = True
        while self._running:
            for gate_name, sensor in self.sensors.items():
                distance = sensor.measure_distance_cm()
                if distance is not None:
                    self.on_reading(gate_name, distance, time.time())
                time.sleep(self.poll_interval_s)

    def stop(self):
        self._running = False
