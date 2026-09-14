"""SQLite 持久化：项目与版本。"""

import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "app.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_no INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (project_id, version_no)
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path=None):
    db_path = path or DB_PATH
    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def create_project(conn, name, payload):
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name, created_at) VALUES (?, ?)", (name, _now()))
    pid = cur.lastrowid
    cur.execute(
        "INSERT INTO versions (project_id, version_no, payload, created_at) VALUES (?, 1, ?, ?)",
        (pid, payload, _now()),
    )
    conn.commit()
    return pid, 1


def add_version(conn, project_id, payload, name=None):
    cur = conn.cursor()
    row = cur.execute("SELECT MAX(version_no) AS v FROM versions WHERE project_id = ?", (project_id,)).fetchone()
    if row is None or cur.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone() is None:
        return None
    next_no = (row["v"] or 0) + 1
    if name is not None:
        cur.execute("UPDATE projects SET name = ? WHERE id = ?", (name, project_id))
    cur.execute(
        "INSERT INTO versions (project_id, version_no, payload, created_at) VALUES (?, ?, ?, ?)",
        (project_id, next_no, payload, _now()),
    )
    conn.commit()
    return next_no


def list_projects(conn):
    rows = conn.execute(
        """
        SELECT p.id, p.name, p.created_at,
               COUNT(v.id) AS versions, MAX(v.created_at) AS updated_at
        FROM projects p LEFT JOIN versions v ON v.project_id = p.id
        GROUP BY p.id ORDER BY p.id DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_project(conn, project_id):
    proj = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if proj is None:
        return None
    ver = conn.execute(
        "SELECT * FROM versions WHERE project_id = ? ORDER BY version_no DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    return {"project": dict(proj), "latest": dict(ver) if ver else None}


def list_versions(conn, project_id):
    if conn.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone() is None:
        return None
    rows = conn.execute(
        "SELECT version_no, created_at FROM versions WHERE project_id = ? ORDER BY version_no DESC",
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_version(conn, project_id, version_no):
    row = conn.execute(
        "SELECT * FROM versions WHERE project_id = ? AND version_no = ?",
        (project_id, version_no),
    ).fetchone()
    return dict(row) if row else None
