import pytest

from main import build_state, on_reading
from storage import get_recent_runs

SAMPLE_CONFIG = {
    'detection': {'history_size': 1, 'min_passage_duration_ms': 50, 'max_passage_duration_s': 5.0},
    'data': {'db_file': ':memory:'},
}
SAMPLE_CALIBRATION = {
    'port_map': {
        '/dev/serial/by-path/board-a': {'1': 'start', '2': 'split1'},
        '/dev/serial/by-path/board-b': {'1': 'finish'},  # '2' left unmapped (unused)
    },
    'thresholds': {'start': 20, 'split1': 20, 'finish': 20},
}


def test_build_state_creates_gates_for_every_calibrated_gate():
    state = build_state(SAMPLE_CONFIG, SAMPLE_CALIBRATION, 'calibration.yaml')
    assert set(state.gates.keys()) == {'start', 'split1', 'finish'}


def test_on_reading_drives_race_engine_through_full_run():
    state = build_state(SAMPLE_CONFIG, SAMPLE_CALIBRATION, 'calibration.yaml')

    on_reading(state, '/dev/serial/by-path/board-a', 1, 35, 0.0)
    on_reading(state, '/dev/serial/by-path/board-a', 1, 10, 0.1)  # start enter
    on_reading(state, '/dev/serial/by-path/board-a', 1, 35, 0.3)  # start exit

    on_reading(state, '/dev/serial/by-path/board-b', 1, 35, 1.0)
    on_reading(state, '/dev/serial/by-path/board-b', 1, 10, 1.1)  # finish enter
    on_reading(state, '/dev/serial/by-path/board-b', 1, 35, 1.3)  # finish exit -> completes run

    assert state.race_engine.current_run is None
    runs = get_recent_runs(state.db_conn)
    assert len(runs) == 1
    assert runs[0]['finish_s'] == pytest.approx(1.2)  # 1.3 - start_ts(0.1)


def test_on_reading_ignores_unmapped_port():
    state = build_state(SAMPLE_CONFIG, SAMPLE_CALIBRATION, 'calibration.yaml')

    on_reading(state, '/dev/serial/by-path/unknown-board', 1, 10, 0.0)

    assert state.race_engine.current_run is None


def test_on_reading_buffers_readings_for_calibration_screen():
    state = build_state(SAMPLE_CONFIG, SAMPLE_CALIBRATION, 'calibration.yaml')

    on_reading(state, '/dev/serial/by-path/board-a', 1, 35, 0.0)

    assert list(state.readings[('/dev/serial/by-path/board-a', '1')]) == [35]
