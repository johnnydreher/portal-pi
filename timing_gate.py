from collections import deque


class TimingGate:
    """Detects robot passage from a stream of distance readings."""

    def __init__(self, threshold_cm=20, history_size=5,
                 min_passage_duration_s=0.05, max_passage_duration_s=5.0):
        self.threshold_cm = threshold_cm
        self.history = deque(maxlen=history_size)
        self.min_passage_duration_s = min_passage_duration_s
        self.max_passage_duration_s = max_passage_duration_s
        self.is_obstructed = False
        self._passage_start = None

    def check_passage(self, distance_cm, timestamp):
        """Feed one distance reading. Returns 'enter', 'exit', or None."""
        self.history.append(distance_cm)
        avg_distance = sum(self.history) / len(self.history)
        currently_obstructed = avg_distance < self.threshold_cm

        if currently_obstructed and not self.is_obstructed:
            self.is_obstructed = True
            self._passage_start = timestamp
            return 'enter'

        if not currently_obstructed and self.is_obstructed:
            self.is_obstructed = False
            duration = timestamp - self._passage_start
            if self.min_passage_duration_s < duration < self.max_passage_duration_s:
                return 'exit'
            return None

        return None
