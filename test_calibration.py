import pytest

from calibration import compute_baseline_and_threshold


def test_computes_threshold_below_baseline():
    baseline, threshold = compute_baseline_and_threshold([34, 35, 33, 34])
    assert baseline == 34.0
    assert threshold == 34.0 - 15  # robot_height(12) + margin(3)


def test_raises_on_empty_samples():
    with pytest.raises(ValueError):
        compute_baseline_and_threshold([])


def test_custom_robot_height_and_margin():
    baseline, threshold = compute_baseline_and_threshold(
        [40, 40], robot_height_cm=10, safety_margin_cm=5
    )
    assert baseline == 40.0
    assert threshold == 25.0
