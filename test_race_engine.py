from race_engine import RaceEngine


def test_full_run_produces_all_splits():
    completed_runs = []
    engine = RaceEngine(on_run_complete=completed_runs.append)

    engine.handle_event('start', 'enter', 0.0)
    engine.handle_event('start', 'exit', 0.2)
    engine.handle_event('split1', 'enter', 1.0)
    result = engine.handle_event('split1', 'exit', 1.2)
    assert result is None  # not finished yet

    engine.handle_event('finish', 'enter', 3.0)
    result = engine.handle_event('finish', 'exit', 3.2)

    assert result is not None
    assert result['splits']['split1'] == 1.2
    assert result['splits']['finish'] == 3.2
    assert completed_runs == [result]


def test_start_gate_exit_does_not_create_a_split():
    engine = RaceEngine()
    engine.handle_event('start', 'enter', 0.0)
    engine.handle_event('start', 'exit', 0.2)
    assert engine.current_run['splits'] == {}


def test_new_start_before_finish_discards_previous_run():
    engine = RaceEngine()
    engine.handle_event('start', 'enter', 0.0)
    engine.handle_event('start', 'exit', 0.2)
    engine.handle_event('split1', 'exit', 1.0)

    engine.handle_event('start', 'enter', 5.0)  # second robot starts before first finished
    assert engine.current_run['start_ts'] == 5.0
    assert engine.current_run['splits'] == {}


def test_manual_reset_discards_current_run():
    engine = RaceEngine()
    engine.handle_event('start', 'enter', 0.0)
    assert engine.current_run is not None
    engine.reset_current_run()
    assert engine.current_run is None


def test_events_before_start_are_ignored():
    engine = RaceEngine()
    result = engine.handle_event('split1', 'exit', 1.0)
    assert result is None
    assert engine.current_run is None
