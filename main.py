"""
Entry point: auto-discovers connected Arduino boards over USB, wires them
into per-gate detection via the saved calibration mapping, and runs the
timing pipeline + Flask dashboard/calibration screen.
"""
import argparse
import threading
from collections import deque

import yaml

from calibration import load_calibration, resolve_gate
from race_engine import RaceEngine
from serial_reader import SerialReader, list_available_ports
from storage import init_db, save_run
from timing_gate import TimingGate
from web import AppState, create_app

BAUD = 9600


def build_state(config, calibration, calibration_path):
    gates = {
        gate: TimingGate(
            threshold_cm=threshold,
            history_size=config['detection']['history_size'],
            min_passage_duration_s=config['detection']['min_passage_duration_ms'] / 1000,
            max_passage_duration_s=config['detection']['max_passage_duration_s'],
        )
        for gate, threshold in calibration['thresholds'].items()
    }
    db_conn = init_db(config['data']['db_file'])

    def on_run_complete(run):
        # A write failure must not crash a background reading thread —
        # log it and keep going (per spec: "not retried automatically").
        try:
            save_run(db_conn, run)
        except Exception as e:
            print(f"ERROR: failed to save run: {e}")

    race_engine = RaceEngine(on_run_complete=on_run_complete)
    return AppState(
        race_engine=race_engine,
        db_conn=db_conn,
        calibration=calibration,
        calibration_path=calibration_path,
        gates=gates,
    )


def on_reading(state, port_id, relative_sensor_id, distance, timestamp):
    key = (port_id, str(relative_sensor_id))
    state.readings.setdefault(key, deque(maxlen=20)).append(distance)

    gate_name = resolve_gate(state.calibration['port_map'], port_id, relative_sensor_id)
    if gate_name and gate_name in state.gates:
        event = state.gates[gate_name].check_passage(distance, timestamp)
        if event:
            state.race_engine.handle_event(gate_name, event, timestamp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--calibration', default='calibration.yaml')
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)
    calibration = load_calibration(args.calibration)

    state = build_state(config, calibration, args.calibration)

    readers = []
    for port in list_available_ports():
        def make_callback(port_id):
            return lambda rel_id, dist, ts: on_reading(state, port_id, rel_id, dist, ts)

        reader = SerialReader(port=port['device'], baud=BAUD, on_reading=make_callback(port['port_id']))
        reader.connect()
        thread = threading.Thread(target=reader.run, daemon=True)
        thread.start()
        readers.append({'port_id': port['port_id'], 'device': port['device'], 'reader': reader})
    state.readers = readers

    app = create_app(state)
    app.run(host=config['web']['host'], port=config['web']['port'])


if __name__ == '__main__':
    main()
