"""SQLite persistence; connections and transactions are scoped to each operation."""

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sqlite3

APPLICATION_COLUMNS = "id, company, role, status, url, notes, follow_up_date, created_at, updated_at"

STATUSES = ("saved", "applied", "interview", "offer", "rejected")


@contextmanager
def connection(path: Path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
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

        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at INTEGER NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS auth_attempts (client TEXT PRIMARY KEY, window_start INTEGER NOT NULL, attempts INTEGER NOT NULL)")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(applications)")}
        if "owner_id" not in columns:
            db.execute("ALTER TABLE applications ADD COLUMN owner_id INTEGER REFERENCES users(id)")


def get_application(path: Path, application_id: int, owner_id: int):
    with connection(path) as db:
        row = db.execute(f"SELECT {APPLICATION_COLUMNS} FROM applications WHERE id = ? AND owner_id = ?", (application_id, owner_id)).fetchone()
        return dict(row) if row else None


def create_application(path: Path, payload: dict, owner_id: int) -> dict:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with connection(path) as db:
        cursor = db.execute("""
            INSERT INTO applications
                (company, role, status, url, notes, follow_up_date, created_at, updated_at, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (payload["company"], payload["role"], payload["status"], payload["url"],
              payload["notes"], payload["follow_up_date"], now, now, owner_id))
        row = db.execute(f"SELECT {APPLICATION_COLUMNS} FROM applications WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def list_applications(path: Path, search: str, status: str | None, limit: int | None, offset: int = 0, *, owner_id: int) -> list[dict]:
    conditions, parameters = ["owner_id = ?"], [owner_id]
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
        rows = db.execute(f"SELECT {APPLICATION_COLUMNS} FROM applications" + clause +
                          " ORDER BY id DESC" + pagination, parameters).fetchall()
        return [dict(row) for row in rows]


def update_application(path: Path, application_id: int, changes: dict, owner_id: int):
    # Column names come from this allowlist; values always use SQL parameters.
    if not changes or not set(changes).issubset({"company", "role", "url", "status", "notes", "follow_up_date"}):
        raise ValueError("Choose company, role, url, status, notes, or follow_up_date to update.")
    changes = {**changes, "updated_at": datetime.now(UTC).isoformat(timespec="seconds")}
    columns = ", ".join(f"{column} = ?" for column in changes)
    with connection(path) as db:
        db.execute(f"UPDATE applications SET {columns} WHERE id = ? AND owner_id = ?",
                   [*changes.values(), application_id, owner_id])
        row = db.execute(f"SELECT {APPLICATION_COLUMNS} FROM applications WHERE id = ? AND owner_id = ?", (application_id, owner_id)).fetchone()
        return dict(row) if row else None


def delete_application(path: Path, application_id: int, owner_id: int) -> bool:
    with connection(path) as db:
        return db.execute("DELETE FROM applications WHERE id = ? AND owner_id = ?", (application_id, owner_id)).rowcount == 1


def statistics(path: Path, owner_id: int) -> dict:
    with connection(path) as db:
        counts = {row["status"]: row["count"] for row in
                  db.execute("SELECT status, COUNT(*) AS count FROM applications WHERE owner_id = ? GROUP BY status", (owner_id,))}
    return {"total": sum(counts.values()), "by_status": {status: counts.get(status, 0) for status in STATUSES}}


def create_user(path: Path, username: str, password_hash: str):
    with connection(path) as db:
        try:
            cursor = db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        except sqlite3.IntegrityError:
            return None
        return {"id": cursor.lastrowid, "username": username}


def find_user(path: Path, username: str):
    with connection(path) as db:
        row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def save_session(path: Path, token_hash: str, user_id: int, expires_at: int):
    with connection(path) as db:
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (expires_at - 86400,))
        db.execute("INSERT INTO sessions VALUES (?, ?, ?)", (token_hash, user_id, expires_at))


def session_user(path: Path, token_hash: str, now: int):
    with connection(path) as db:
        row = db.execute("SELECT users.id, users.username FROM sessions JOIN users ON users.id = sessions.user_id WHERE token_hash = ? AND expires_at > ?", (token_hash, now)).fetchone()
        return dict(row) if row else None


def delete_session(path: Path, token_hash: str):
    with connection(path) as db:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def allow_auth_attempt(path: Path, client: str, now: int) -> bool:
    """Allow at most 20 login/registration attempts per client in 60 seconds."""
    with connection(path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM auth_attempts WHERE window_start <= ?", (now - 60,))
        db.execute("INSERT INTO auth_attempts VALUES (?, ?, 1) ON CONFLICT(client) DO UPDATE SET attempts = attempts + 1", (client, now))
        return db.execute("SELECT attempts FROM auth_attempts WHERE client = ?", (client,)).fetchone()[0] <= 20


def claim_legacy_applications(path: Path, username: str) -> int:
    """Local administrator operation; never exposed through the API."""
    with connection(path) as db:
        user = db.execute("SELECT id FROM users WHERE username = ?", (username.lower(),)).fetchone()
        if user is None:
            raise ValueError("Register this account before assigning legacy records.")
        return db.execute("UPDATE applications SET owner_id = ? WHERE owner_id IS NULL", (user["id"],)).rowcount
