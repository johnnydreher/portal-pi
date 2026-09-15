"""
Samples each sensor's empty-track baseline directly via GPIO and writes
suggested thresholds into config.yaml.

Usage: python3 calibration.py --config config.yaml --samples 20
"""
import argparse
import time

import yaml

from gpio_reader import GpioSensor

GATE_NAMES = ('start', 'split1', 'split2', 'finish')


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


def collect_samples(sensors, samples_per_sensor):
    """sensors: dict[str, GpioSensor]. Returns dict[str, list[float]]."""
    collected = {name: [] for name in sensors}
    for name, sensor in sensors.items():
        while len(collected[name]) < samples_per_sensor:
            distance = sensor.measure_distance_cm()
            if distance is not None:
                collected[name].append(distance)
            time.sleep(0.05)
    return collected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--samples', type=int, default=20)
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    sensors = {
        name: GpioSensor(config['gpio'][name]['trigger'], config['gpio'][name]['echo'])
        for name in GATE_NAMES
    }

    input("Make sure the track is empty, then press ENTER...")
    collected = collect_samples(sensors, args.samples)

    for name, samples in collected.items():
        baseline, threshold = compute_baseline_and_threshold(samples)
        config['calibration']['thresholds'][name] = round(threshold, 1)
        print(f"{name}: baseline={baseline:.1f}cm threshold={threshold:.1f}cm")

    with open(args.config, 'w') as f:
        yaml.safe_dump(config, f)

    print(f"\nSaved thresholds to {args.config}")


if __name__ == '__main__':
    main()
