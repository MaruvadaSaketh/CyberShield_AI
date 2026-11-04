import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.config import settings

_MAX_INCIDENTS = 500
_lock = Lock()


def _connect() -> sqlite3.Connection:
    database_path = Path(settings.database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=30)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            severity TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    return connection


def add_incident(payload: dict) -> dict:
    now = datetime.now(timezone.utc)
    item = {
        "incident_id": f"CS-{now.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6].upper()}",
        "created_at": now.isoformat(),
        **payload,
    }
    with _lock:
        with closing(_connect()) as connection, connection:
            connection.execute(
                "INSERT INTO incidents (incident_id, created_at, severity, payload) "
                "VALUES (?, ?, ?, ?)",
                (
                    item["incident_id"],
                    item["created_at"],
                    item["severity"],
                    json.dumps(item),
                ),
            )
            connection.execute(
                "DELETE FROM incidents WHERE id NOT IN "
                "(SELECT id FROM incidents ORDER BY id DESC LIMIT ?)",
                (_MAX_INCIDENTS,),
            )
    return item


def list_incidents(severity: str | None = None) -> list[dict]:
    with _lock:
        with closing(_connect()) as connection:
            if severity:
                rows = connection.execute(
                    "SELECT payload FROM incidents WHERE severity = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (severity.upper(), _MAX_INCIDENTS),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload FROM incidents ORDER BY id DESC LIMIT ?",
                    (_MAX_INCIDENTS,),
                ).fetchall()
    return [json.loads(row[0]) for row in rows]
