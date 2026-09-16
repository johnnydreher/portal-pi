import pytest

from calibration import compute_baseline_and_threshold, load_calibration, resolve_gate, save_calibration


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


def test_load_calibration_defaults_when_file_missing(tmp_path):
    data = load_calibration(str(tmp_path / 'missing.yaml'))
    assert data == {'port_map': {}, 'thresholds': {}}


def test_save_then_load_calibration_round_trips(tmp_path):
    path = str(tmp_path / 'calibration.yaml')
    data = {'port_map': {'portA': {'1': 'start', '2': 'split1'}}, 'thresholds': {'start': 19.5}}

    save_calibration(path, data)
    loaded = load_calibration(path)

    assert loaded == data


def test_resolve_gate_returns_mapped_name():
    port_map = {'portA': {'1': 'start', '2': 'split1'}}
    assert resolve_gate(port_map, 'portA', 1) == 'start'
    assert resolve_gate(port_map, 'portA', 2) == 'split1'


def test_resolve_gate_returns_none_when_unmapped():
    port_map = {'portA': {'1': 'start'}}
    assert resolve_gate(port_map, 'portA', 2) is None
    assert resolve_gate(port_map, 'portB', 1) is None
