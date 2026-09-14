from storage import init_db, save_run, get_recent_runs


def test_save_and_retrieve_run():
    conn = init_db(':memory:')
    run = {'start_ts': 100.0, 'splits': {'split1': 1.2, 'split2': 2.4, 'finish': 3.6}}

    row_id = save_run(conn, run)
    assert row_id == 1

    runs = get_recent_runs(conn)
    assert len(runs) == 1
    assert runs[0]['split1_s'] == 1.2
    assert runs[0]['split2_s'] == 2.4
    assert runs[0]['finish_s'] == 3.6


def test_recent_runs_newest_first():
    conn = init_db(':memory:')
    save_run(conn, {'start_ts': 1.0, 'splits': {'finish': 1.0}})
    save_run(conn, {'start_ts': 2.0, 'splits': {'finish': 2.0}})

    runs = get_recent_runs(conn)
    assert runs[0]['start_ts'] == 2.0
    assert runs[1]['start_ts'] == 1.0


def test_recent_runs_respects_limit():
    conn = init_db(':memory:')
    for i in range(5):
        save_run(conn, {'start_ts': float(i), 'splits': {}})

    runs = get_recent_runs(conn, limit=2)
    assert len(runs) == 2
