"""
Samples each sensor's empty-track baseline over the RS485 bus and writes
suggested thresholds into config.yaml.

Usage: python3 calibration.py --port /dev/ttyUSB0 --baud 9600 --samples 20
"""
import argparse
import time

import serial
import yaml

from serial_reader import parse_frame

GATE_NAMES = {1: 'start', 2: 'split1', 3: 'split2', 4: 'finish'}


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


def collect_samples(port, baud, samples_per_sensor, timeout_s=15):
    """Reads frames until `samples_per_sensor` readings are collected per sensor ID (1-4)."""
    ser = serial.Serial(port, baud, timeout=1)
    collected = {1: [], 2: [], 3: [], 4: []}
    deadline = time.time() + timeout_s
    while time.time() < deadline and any(len(v) < samples_per_sensor for v in collected.values()):
        raw = ser.readline().decode('utf-8', errors='ignore')
        parsed = parse_frame(raw)
        if parsed:
            sensor_id, distance = parsed
            if len(collected[sensor_id]) < samples_per_sensor:
                collected[sensor_id].append(distance)
    ser.close()
    return collected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='/dev/ttyUSB0')
    parser.add_argument('--baud', type=int, default=9600)
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--config', default='config.yaml')
    args = parser.parse_args()

    input("Make sure the track is empty, then press ENTER...")
    collected = collect_samples(args.port, args.baud, args.samples)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    for sensor_id, samples in collected.items():
        if not samples:
            print(f"WARNING: no samples collected for sensor {sensor_id}, skipping")
            continue
        baseline, threshold = compute_baseline_and_threshold(samples)
        gate_name = GATE_NAMES[sensor_id]
        config['calibration']['thresholds'][gate_name] = round(threshold, 1)
        print(f"{gate_name}: baseline={baseline:.1f}cm threshold={threshold:.1f}cm")

    with open(args.config, 'w') as f:
        yaml.safe_dump(config, f)

    print(f"\nSaved thresholds to {args.config}")


if __name__ == '__main__':
    main()
