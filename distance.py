SPEED_OF_SOUND_CM_PER_S = 34300


def pulse_duration_to_cm(duration_s):
    """Convert an HC-SR04 echo pulse duration to distance in cm, clamped to its 2-400cm valid range."""
    distance = (duration_s * SPEED_OF_SOUND_CM_PER_S) / 2
    return max(2.0, min(400.0, distance))
