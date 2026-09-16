from collections import deque

import calibration as calibration_module
from race_engine import RaceEngine
from storage import init_db, save_run
from timing_gate import TimingGate
from web import AppState, create_app


class FakeReader:
    def __init__(self, connected=True):
        self.connected = connected


def make_state(calibration=None, readers=None, gates=None, calibration_path='calibration.yaml'):
    race_engine = RaceEngine()
    conn = init_db(':memory:')
    return AppState(
        race_engine=race_engine,
        db_conn=conn,
        calibration=calibration or {'port_map': {}, 'thresholds': {}},
        calibration_path=calibration_path,
        gates=gates if gates is not None else {name: TimingGate() for name in ('start', 'split1', 'split2', 'finish')},
        readers=readers or [],
    )


def test_status_returns_gate_state():
    state = make_state()
    client = create_app(state).test_client()

    response = client.get('/api/status')
    data = response.get_json()

    assert data['connected'] is False
    assert data['current_run'] is None
    assert set(data['gates'].keys()) == {'start', 'split1', 'split2', 'finish'}


def test_results_returns_saved_runs():
    state = make_state()
    save_run(state.db_conn, {'start_ts': 1.0, 'splits': {'finish': 3.5}})
    client = create_app(state).test_client()

    response = client.get('/api/results')
    data = response.get_json()

    assert data['count'] == 1
    assert data['runs'][0]['finish_s'] == 3.5


def test_reset_clears_current_run():
    state = make_state()
    state.race_engine.handle_event('start', 'enter', 0.0)
    client = create_app(state).test_client()

    response = client.post('/api/reset')

    assert response.get_json() == {'ok': True}
    assert state.race_engine.current_run is None


def test_index_serves_dashboard():
    state = make_state()
    client = create_app(state).test_client()

    response = client.get('/')

    assert response.status_code == 200
    assert b'Race Timing' in response.data


def test_calibration_page_serves_html():
    state = make_state()
    client = create_app(state).test_client()

    response = client.get('/calibration')

    assert response.status_code == 200
    assert b'Calibra' in response.data


def test_calibration_ports_lists_connected_ports_with_live_readings():
    state = make_state(
        calibration={'port_map': {'portA': {'1': 'start'}}, 'thresholds': {}},
        readers=[{'port_id': 'portA', 'device': '/dev/ttyUSB0', 'reader': FakeReader()}],
    )
    state.readings[('portA', '1')] = deque([30, 31, 29], maxlen=20)
    client = create_app(state).test_client()

    response = client.get('/api/calibration/ports')
    data = response.get_json()

    port = data['ports'][0]
    assert port['port_id'] == 'portA'
    assert port['connected'] is True
    assert port['sensors']['1']['distance'] == 29
    assert port['sensors']['1']['gate'] == 'start'
    assert port['sensors']['2']['distance'] is None
    assert port['sensors']['2']['gate'] is None


def test_calibration_map_saves_assignment(tmp_path):
    calibration_path = str(tmp_path / 'calibration.yaml')
    state = make_state(calibration_path=calibration_path)
    client = create_app(state).test_client()

    response = client.post('/api/calibration/map', json={
        'assignments': [{'port_id': 'portA', 'sensor': 1, 'gate': 'start'}],
    })

    assert response.get_json()['ok'] is True
    assert response.get_json()['duplicate_gates'] == []
    assert state.calibration['port_map']['portA']['1'] == 'start'
    saved = calibration_module.load_calibration(calibration_path)
    assert saved['port_map']['portA']['1'] == 'start'


def test_calibration_map_flags_duplicate_gate_assignment(tmp_path):
    state = make_state(calibration_path=str(tmp_path / 'calibration.yaml'))
    client = create_app(state).test_client()

    response = client.post('/api/calibration/map', json={
        'assignments': [
            {'port_id': 'portA', 'sensor': 1, 'gate': 'start'},
            {'port_id': 'portB', 'sensor': 1, 'gate': 'start'},
        ],
    })

    assert response.get_json()['duplicate_gates'] == ['start']


def test_calibration_measure_computes_threshold_from_buffered_readings():
    state = make_state(calibration={'port_map': {'portA': {'1': 'start'}}, 'thresholds': {}})
    state.readings[('portA', '1')] = deque([34, 35, 33, 34], maxlen=20)
    client = create_app(state).test_client()

    response = client.post('/api/calibration/measure/start')
    data = response.get_json()

    assert data['baseline_cm'] == 34.0
    assert data['threshold_cm'] == 19.0


def test_calibration_measure_errors_when_no_readings_yet():
    state = make_state()
    client = create_app(state).test_client()

    response = client.post('/api/calibration/measure/start')

    assert response.status_code == 400


def test_calibration_thresholds_saves_and_rebuilds_gate(tmp_path):
    calibration_path = str(tmp_path / 'calibration.yaml')
    state = make_state(calibration_path=calibration_path)
    client = create_app(state).test_client()

    response = client.post('/api/calibration/thresholds', json={'gate': 'start', 'threshold_cm': 19.0})

    assert response.get_json() == {'ok': True}
    assert state.gates['start'].threshold_cm == 19.0
    saved = calibration_module.load_calibration(calibration_path)
    assert saved['thresholds']['start'] == 19.0
