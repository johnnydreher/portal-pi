GATE_ORDER = ('start', 'split1', 'split2', 'finish')


class RaceEngine:
    """Sequences gate enter/exit events from all 4 portals into completed runs."""

    def __init__(self, on_run_complete=None):
        self.current_run = None
        self.on_run_complete = on_run_complete

    def handle_event(self, gate_name, event_type, timestamp):
        """
        gate_name: one of GATE_ORDER
        event_type: 'enter' or 'exit'
        timestamp: float (seconds, time.time())

        Returns the completed run dict if this event finished a run, else None.
        """
        if gate_name not in GATE_ORDER:
            raise ValueError(f"Unknown gate: {gate_name}")

        if gate_name == 'start' and event_type == 'enter':
            self.current_run = {'start_ts': timestamp, 'splits': {}}
            return None

        if self.current_run is None:
            return None

        if event_type == 'exit' and gate_name != 'start':
            delta = timestamp - self.current_run['start_ts']
            self.current_run['splits'][gate_name] = delta

            if gate_name == 'finish':
                completed = self.current_run
                self.current_run = None
                if self.on_run_complete:
                    self.on_run_complete(completed)
                return completed

        return None

    def reset_current_run(self):
        """Discard the in-progress run (manual operator reset)."""
        self.current_run = None
