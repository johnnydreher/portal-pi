import pytest

from main import GATE_NAMES, build_state, on_reading
from storage import get_recent_runs

SAMPLE_CONFIG = {
    'calibration': {'thresholds': {'start': 20, 'split1': 20, 'split2': 20, 'finish': 20}},
    'detection': {'history_size': 1, 'min_passage_duration_ms': 50, 'max_passage_duration_s': 5.0},
    'data': {'db_file': ':memory:'},
}


def test_build_state_creates_all_gates():
    state = build_state(SAMPLE_CONFIG)
    assert set(state.gates.keys()) == set(GATE_NAMES)


def test_on_reading_drives_race_engine_through_full_run():
    state = build_state(SAMPLE_CONFIG)

    on_reading(state, 'start', 35, 0.0)
    on_reading(state, 'start', 10, 0.1)  # start enter
    on_reading(state, 'start', 35, 0.3)  # start exit

    on_reading(state, 'finish', 35, 1.0)
    on_reading(state, 'finish', 10, 1.1)  # finish enter
    on_reading(state, 'finish', 35, 1.3)  # finish exit -> completes run

    assert state.race_engine.current_run is None
    runs = get_recent_runs(state.db_conn)
    assert len(runs) == 1
    assert runs[0]['finish_s'] == pytest.approx(1.2)  # 1.3 - start_ts(0.1)
