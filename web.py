from flask import Flask, jsonify, render_template

from storage import get_recent_runs


class AppState:
    """Shared state Flask routes read from; updated by the background thread."""

    def __init__(self, gates, race_engine, db_conn, reader=None):
        self.gates = gates              # dict[str, TimingGate]
        self.race_engine = race_engine  # RaceEngine
        self.db_conn = db_conn          # sqlite3 connection
        self.reader = reader            # SerialReader, set once connected (may be None)


def create_app(state):
    app = Flask(__name__)

    @app.route('/')
    def index():
        return render_template('dashboard.html')

    @app.route('/api/status')
    def api_status():
        return jsonify({
            'connected': bool(state.reader and state.reader.connected),
            'current_run': state.race_engine.current_run,
            'gates': {name: gate.is_obstructed for name, gate in state.gates.items()},
        })

    @app.route('/api/results')
    def api_results():
        runs = get_recent_runs(state.db_conn, limit=50)
        return jsonify({'count': len(runs), 'runs': runs})

    @app.route('/api/reset', methods=['POST'])
    def api_reset():
        state.race_engine.reset_current_run()
        return jsonify({'ok': True})

    return app
