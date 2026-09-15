import pytest

from distance import pulse_duration_to_cm


def test_converts_duration_to_distance():
    # 30cm round trip at 34300 cm/s -> duration = 2*30/34300
    duration_s = (2 * 30) / 34300
    assert pulse_duration_to_cm(duration_s) == pytest.approx(30.0)


def test_clamps_to_minimum_2cm():
    assert pulse_duration_to_cm(0) == 2.0


def test_clamps_to_maximum_400cm():
    assert pulse_duration_to_cm(1.0) == 400.0
