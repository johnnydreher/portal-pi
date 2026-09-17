from flask import Flask, jsonify, render_template, request

from calibration import compute_baseline_and_threshold, resolve_gate, save_calibration
from storage import get_recent_runs
from timing_gate import TimingGate

GATE_CHOICES = ('start', 'split1', 'finish')


class AppState:
    """Shared state Flask routes read from; updated by the background threads."""

    def __init__(self, race_engine, db_conn, calibration, calibration_path, gates=None, readers=None):
        self.race_engine = race_engine
        self.db_conn = db_conn
        self.calibration = calibration            # {'port_map': {...}, 'thresholds': {...}}
        self.calibration_path = calibration_path
        self.gates = gates if gates is not None else {}   # dict[str, TimingGate], one per calibrated gate
        self.readers = readers or []               # list[dict]: port_id, device, reader
        self.readings = {}                          # {(port_id, relative_id_str): deque[float]}, last 20 raw readings


def _find_reading_key(state, gate):
    for port_id, sensors in state.calibration.get('port_map', {}).items():
        for relative_id, mapped_gate in sensors.items():
            if mapped_gate == gate:
                return (port_id, relative_id)
    return None


def create_app(state):
    app = Flask(__name__)

    @app.route('/')
    def index():
        return render_template('dashboard.html')

    @app.route('/calibration')
    def calibration_page():
        return render_template('calibration.html')

    @app.route('/api/status')
    def api_status():
        return jsonify({
            'connected': bool(state.readers) and all(r['reader'].connected for r in state.readers),
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

    @app.route('/api/calibration/ports')
    def api_calibration_ports():
        port_map = state.calibration.get('port_map', {})
        ports = []
        for entry in state.readers:
            port_id, reader = entry['port_id'], entry['reader']
            sensors = {}
            for relative_id in ('1', '2'):
                buf = state.readings.get((port_id, relative_id))
                sensors[relative_id] = {
                    'distance': buf[-1] if buf else None,
                    'gate': resolve_gate(port_map, port_id, int(relative_id)),
                }
            ports.append({
                'port_id': port_id,
                'device': entry['device'],
                'connected': reader.connected,
                'sensors': sensors,
            })
        return jsonify({'ports': ports, 'gate_choices': list(GATE_CHOICES)})

    @app.route('/api/calibration/map', methods=['POST'])
    def api_calibration_map():
        body = request.get_json()
        port_map = state.calibration.setdefault('port_map', {})
        for assignment in body['assignments']:
            port_id = assignment['port_id']
            relative_id = str(assignment['sensor'])
            gate = assignment['gate']
            entry = port_map.setdefault(port_id, {})
            if gate:
                entry[relative_id] = gate
            else:
                entry.pop(relative_id, None)
        save_calibration(state.calibration_path, state.calibration)

        assigned = [g for sensors in port_map.values() for g in sensors.values()]
        duplicates = sorted({g for g in assigned if assigned.count(g) > 1})

        return jsonify({'ok': True, 'port_map': state.calibration['port_map'], 'duplicate_gates': duplicates})

    @app.route('/api/calibration/measure/<gate>', methods=['POST'])
    def api_calibration_measure(gate):
        key = _find_reading_key(state, gate)
        samples = list(state.readings.get(key, [])) if key else []
        if not samples:
            return jsonify({'error': 'no readings yet for this gate'}), 400
        baseline, threshold = compute_baseline_and_threshold(samples)
        return jsonify({
            'baseline_cm': round(baseline, 1),
            'threshold_cm': round(threshold, 1),
            'samples': len(samples),
        })

    @app.route('/api/calibration/thresholds', methods=['POST'])
    def api_calibration_thresholds():
        body = request.get_json()
        gate, threshold_cm = body['gate'], body['threshold_cm']
        state.calibration.setdefault('thresholds', {})[gate] = threshold_cm
        save_calibration(state.calibration_path, state.calibration)
        state.gates[gate] = TimingGate(threshold_cm=threshold_cm)
        return jsonify({'ok': True})

    return app
