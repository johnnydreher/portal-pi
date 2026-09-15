"""
Samples each sensor's empty-track baseline over both Arduino boards' USB
ports and writes suggested thresholds into config.yaml.

Usage: python3 calibration.py --config config.yaml --samples 20
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


def collect_samples(boards, samples_per_sensor, timeout_s=15):
    """
    boards: list of (port, baud) tuples, one per Arduino.
    Reads frames from all boards until `samples_per_sensor` readings are
    collected per sensor ID (1-4). Returns dict[int, list[float]].
    """
    serials = [serial.Serial(port, baud, timeout=1) for port, baud in boards]
    collected = {1: [], 2: [], 3: [], 4: []}
    deadline = time.time() + timeout_s
    while time.time() < deadline and any(len(v) < samples_per_sensor for v in collected.values()):
        for ser in serials:
            if ser.in_waiting:
                raw = ser.readline().decode('utf-8', errors='ignore')
                parsed = parse_frame(raw)
                if parsed:
                    sensor_id, distance = parsed
                    if len(collected[sensor_id]) < samples_per_sensor:
                        collected[sensor_id].append(distance)
    for ser in serials:
        ser.close()
    return collected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--samples', type=int, default=20)
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    boards = [(b['port'], b['baud']) for b in config['serial']['boards']]

    input("Make sure the track is empty, then press ENTER...")
    collected = collect_samples(boards, args.samples)

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
