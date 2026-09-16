import os

from serial_reader import _resolve_by_path_map, list_available_ports, parse_frame


class FakePortInfo:
    def __init__(self, device):
        self.device = device


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


def test_list_available_ports_falls_back_to_device_when_no_by_path_dir():
    ports = list_available_ports(
        comports_fn=lambda: [FakePortInfo('/dev/ttyUSB0'), FakePortInfo('/dev/ttyUSB1')],
        by_path_dir='C:/nonexistent/for/test',
    )
    assert ports == [
        {'port_id': '/dev/ttyUSB0', 'device': '/dev/ttyUSB0'},
        {'port_id': '/dev/ttyUSB1', 'device': '/dev/ttyUSB1'},
    ]


def test_list_available_ports_prefers_by_path_id_when_resolvable(monkeypatch):
    monkeypatch.setattr(os.path, 'isdir', lambda path: True)
    monkeypatch.setattr(os, 'listdir', lambda path: ['usb-Arduino-if00'])
    monkeypatch.setattr(os.path, 'realpath', lambda path: '/dev/ttyUSB0')

    ports = list_available_ports(
        comports_fn=lambda: [FakePortInfo('/dev/ttyUSB0')],
        by_path_dir='/dev/serial/by-path',
    )

    assert ports == [{'port_id': os.path.join('/dev/serial/by-path', 'usb-Arduino-if00'), 'device': '/dev/ttyUSB0'}]


def test_resolve_by_path_map_empty_when_dir_missing():
    assert _resolve_by_path_map('C:/nonexistent/for/test') == {}
