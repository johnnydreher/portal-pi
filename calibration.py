"""
Calibration data: which (USB port, relative sensor id) maps to which gate,
and each gate's detection threshold. Written by the web calibration screen
(web.py) — this module has no CLI or hardware access of its own.
"""
import yaml


def compute_baseline_and_threshold(samples, robot_height_cm=12, safety_margin_cm=3):
    """
    samples: list of empty-track distance readings (cm)
    Returns (baseline_cm, threshold_cm).
    """
    if not samples:
        raise ValueError("Need at least one sample")
    baseline = sum(samples) / len(samples)
    threshold = baseline - (robot_height_cm + safety_margin_cm)
    return baseline, threshold


def load_calibration(path):
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}
    data.setdefault('port_map', {})
    data.setdefault('thresholds', {})
    return data


def save_calibration(path, data):
    with open(path, 'w') as f:
        yaml.safe_dump(data, f)


def resolve_gate(port_map, port_id, relative_sensor_id):
    """port_map: {port_id: {'1': gate_name, '2': gate_name}}. Returns the gate
    name for this (port, relative sensor id), or None if not yet mapped."""
    return port_map.get(port_id, {}).get(str(relative_sensor_id))
