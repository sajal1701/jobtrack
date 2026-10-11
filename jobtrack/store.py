"""SQLite persistence; connections and transactions are scoped to each operation."""

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sqlite3

STATUSES = ("saved", "applied", "interview", "offer", "rejected")


@contextmanager
def connection(path: Path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connection(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN
                    ('saved', 'applied', 'interview', 'offer', 'rejected')),
                url TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                follow_up_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def get_application(path: Path, application_id: int):
    with connection(path) as db:
        row = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        return dict(row) if row else None


def create_application(path: Path, payload: dict) -> dict:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with connection(path) as db:
        cursor = db.execute("""
            INSERT INTO applications
                (company, role, status, url, notes, follow_up_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (payload["company"], payload["role"], payload["status"], payload["url"],
              payload["notes"], payload["follow_up_date"], now, now))
        row = db.execute("SELECT * FROM applications WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def list_applications(path: Path, search: str, status: str | None, limit: int | None, offset: int = 0) -> list[dict]:
    conditions, parameters = [], []
    if search:
        # Escape LIKE metacharacters so a search is literal, rather than a pattern.
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append("(company LIKE ? ESCAPE '\\' OR role LIKE ? ESCAPE '\\')")
        parameters.extend([f"%{escaped}%"] * 2)
    if status:
        conditions.append("status = ?")
        parameters.append(status)
    clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    pagination = ""
    if limit is not None:
        pagination = " LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
    with connection(path) as db:
        rows = db.execute("SELECT * FROM applications" + clause +
                          " ORDER BY id DESC" + pagination, parameters).fetchall()
        return [dict(row) for row in rows]


def update_application(path: Path, application_id: int, changes: dict):
    # Column names come from this allowlist; values always use SQL parameters.
    if not changes or not set(changes).issubset({"status", "notes", "follow_up_date"}):
        raise ValueError("Choose status, notes, or follow_up_date to update.")
    changes = {**changes, "updated_at": datetime.now(UTC).isoformat(timespec="seconds")}
    columns = ", ".join(f"{column} = ?" for column in changes)
    with connection(path) as db:
        db.execute(f"UPDATE applications SET {columns} WHERE id = ?",
                   [*changes.values(), application_id])
        row = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        return dict(row) if row else None


def delete_application(path: Path, application_id: int) -> bool:
    with connection(path) as db:
        return db.execute("DELETE FROM applications WHERE id = ?", (application_id,)).rowcount == 1


def statistics(path: Path) -> dict:
    with connection(path) as db:
        counts = {row["status"]: row["count"] for row in
                  db.execute("SELECT status, COUNT(*) AS count FROM applications GROUP BY status")}
    return {"total": sum(counts.values()), "by_status": {status: counts.get(status, 0) for status in STATUSES}}
