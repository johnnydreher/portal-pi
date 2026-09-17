import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ts REAL NOT NULL,
    split1_s REAL,
    finish_s REAL,
    created_at TEXT NOT NULL
);
"""


def init_db(path):
    """Open (creating if needed) the SQLite DB and ensure the schema exists."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def save_run(conn, run):
    """
    Persist a completed run.
    run: {'start_ts': float, 'splits': {'split1': float, 'finish': float}}
    Returns the new row id.
    """
    splits = run['splits']
    cursor = conn.execute(
        "INSERT INTO runs (start_ts, split1_s, finish_s, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            run['start_ts'],
            splits.get('split1'),
            splits.get('finish'),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_recent_runs(conn, limit=50):
    """Return the most recent runs, newest first, as a list of dicts."""
    cursor = conn.execute(
        "SELECT id, start_ts, split1_s, finish_s, created_at "
        "FROM runs ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
