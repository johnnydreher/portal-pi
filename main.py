"""
Entry point: wires the GPIO reader, timing gates, race engine, storage,
and the Flask web app together, then runs the web server.
"""
import argparse
import threading

import yaml

from gpio_reader import GpioReader, GpioSensor
from race_engine import RaceEngine
from storage import init_db, save_run
from timing_gate import TimingGate
from web import AppState, create_app

GATE_NAMES = ('start', 'split1', 'split2', 'finish')


def build_state(config):
    gates = {
        name: TimingGate(
            threshold_cm=config['calibration']['thresholds'][name],
            history_size=config['detection']['history_size'],
            min_passage_duration_s=config['detection']['min_passage_duration_ms'] / 1000,
            max_passage_duration_s=config['detection']['max_passage_duration_s'],
        )
        for name in GATE_NAMES
    }
    db_conn = init_db(config['data']['db_file'])

    def on_run_complete(run):
        # A write failure must not crash the background GPIO-polling thread —
        # log it and keep going (per spec: "not retried automatically").
        try:
            save_run(db_conn, run)
        except Exception as e:
            print(f"ERROR: failed to save run: {e}")

    race_engine = RaceEngine(on_run_complete=on_run_complete)
    return AppState(gates=gates, race_engine=race_engine, db_conn=db_conn)


def on_reading(state, gate_name, distance, timestamp):
    event = state.gates[gate_name].check_passage(distance, timestamp)
    if event:
        state.race_engine.handle_event(gate_name, event, timestamp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.yaml')
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    state = build_state(config)

    sensors = {
        name: GpioSensor(config['gpio'][name]['trigger'], config['gpio'][name]['echo'])
        for name in GATE_NAMES
    }
    reader = GpioReader(
        sensors=sensors,
        on_reading=lambda gate, dist, ts: on_reading(state, gate, dist, ts),
    )
    reader.connect()
    state.reader = reader
    thread = threading.Thread(target=reader.run, daemon=True)
    thread.start()

    app = create_app(state)
    app.run(host=config['web']['host'], port=config['web']['port'])


if __name__ == '__main__':
    main()
