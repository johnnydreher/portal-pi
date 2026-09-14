from timing_gate import TimingGate


def test_enter_detected_when_distance_drops_below_threshold():
    gate = TimingGate(threshold_cm=20, history_size=1)
    assert gate.check_passage(35, timestamp=0.0) is None
    assert gate.check_passage(10, timestamp=0.1) == 'enter'


def test_exit_detected_when_distance_returns_above_threshold():
    gate = TimingGate(threshold_cm=20, history_size=1)
    gate.check_passage(35, timestamp=0.0)
    gate.check_passage(10, timestamp=0.1)
    assert gate.check_passage(35, timestamp=0.3) == 'exit'


def test_short_passage_rejected_as_noise():
    gate = TimingGate(threshold_cm=20, history_size=1, min_passage_duration_s=0.05)
    gate.check_passage(35, timestamp=0.0)
    gate.check_passage(10, timestamp=0.1)
    assert gate.check_passage(35, timestamp=0.11) is None


def test_long_passage_rejected():
    gate = TimingGate(threshold_cm=20, history_size=1, max_passage_duration_s=1.0)
    gate.check_passage(35, timestamp=0.0)
    gate.check_passage(10, timestamp=0.1)
    assert gate.check_passage(35, timestamp=2.0) is None


def test_smoothing_averages_history():
    gate = TimingGate(threshold_cm=20, history_size=3)
    gate.check_passage(35, timestamp=0.0)
    gate.check_passage(35, timestamp=0.05)
    result = gate.check_passage(5, timestamp=0.1)  # avg = (35+35+5)/3 = 25, still above 20
    assert result is None
