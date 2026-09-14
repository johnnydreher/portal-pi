from race_engine import RaceEngine
from storage import init_db, save_run
from timing_gate import TimingGate
from web import AppState, create_app


def make_state():
    gates = {name: TimingGate() for name in ('start', 'split1', 'split2', 'finish')}
    race_engine = RaceEngine()
    conn = init_db(':memory:')
    return AppState(gates=gates, race_engine=race_engine, db_conn=conn)


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
