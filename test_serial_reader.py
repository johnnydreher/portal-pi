from serial_reader import parse_frame


def test_parses_valid_frame():
    assert parse_frame('[1,35]') == (1, 35)


def test_parses_frame_with_whitespace():
    assert parse_frame('[2,120]\r\n') == (2, 120)


def test_rejects_malformed_frame():
    assert parse_frame('garbage') is None
    assert parse_frame('[1,abc]') is None
    assert parse_frame('') is None


def test_rejects_out_of_range_sensor_id():
    assert parse_frame('[5,35]') is None
    assert parse_frame('[0,35]') is None


def test_rejects_out_of_range_distance():
    assert parse_frame('[1,1]') is None
    assert parse_frame('[1,500]') is None
