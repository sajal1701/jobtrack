# Developing JobTrack

Start with [the user guide](README.md) to install and run the app. This document
covers the code structure, API behavior, and checks for contributors.

## Project structure

| Path | Responsibility |
| --- | --- |
| `jobtrack/api.py` | FastAPI routes, request validation, and static file serving |
| `jobtrack/auth.py` | Salted scrypt password hashing and session token hashing |
| `jobtrack/store.py` | SQLite schema, queries, and transactions |
| `web/` | Browser interface, styles, and application state |
| `tests/` | API/authentication tests with temporary databases and client authentication checks |
| `scripts/` | Setup, local server, and test commands |
| `.github/workflows/ci.yml` | Checks for pushes and pull requests |

## Architecture

`web/` is the browser client. `jobtrack/api.py` validates HTTP input and maps
missing records to HTTP errors. `jobtrack/store.py` owns SQLite operations.
`create_app(db_path)` makes it possible to test persistence without touching
personal data. The server serves the UI and API from the same origin.

SQLite keeps local setup simple: there is no separate database server to run.
The browser uses plain JavaScript, and serving it from FastAPI keeps the UI and
API on the same origin. A future React migration can reuse the existing API.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Health check |
| GET | `/api/applications` | Search, filter, and paginate |
| GET | `/api/applications/export` | Download all matching applications as CSV |
| POST | `/api/applications` | Create an application |
| GET | `/api/applications/{id}` | Read one application |
| PATCH | `/api/applications/{id}` | Edit company, role, URL, stage, notes, or follow-up date |
| DELETE | `/api/applications/{id}` | Delete one application |
| GET | `/api/stats` | Counts for all applications |

Interactive API documentation is available at `http://127.0.0.1:8010/docs`
while the server is running.

The list endpoint accepts `search`, `status`, `limit` (1–100, default 100), and
`offset` (default 0). Results are ordered by descending ID. Search matches
company or role and treats `%` and `_` as literal characters. Statistics count
all applications, regardless of list filters.

CSV export accepts the same `search` and `status` filters and ordering as the
list endpoint, without pagination. It returns `text/csv` with an attachment
filename of `jobtrack-applications.csv`. Null dates become empty cells, and an
empty result contains the header row.

PATCH preserves omitted fields. Set `follow_up_date` to `null` to clear it;
Company, role, URL, status, and notes cannot be null. Company, role, and URL
reuse creation validation, including whitespace trimming and HTTP(S) link
validation. Set `url` to an empty string to remove a link. An empty patch
returns 400, invalid input returns 422, and missing records return 404.

## Authentication and ownership

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Create an account and start a session |
| POST | `/api/auth/login` | Verify credentials and start a session |
| GET | `/api/auth/me` | Read the signed-in account |
| POST | `/api/auth/logout` | Revoke the current session |

Registration/login accept JSON `username` and `password`. All application and
statistics endpoints require a session cookie and return 401 without one.
Records owned by another account return 404. Responses keep the existing
application fields; the server determines ownership from the session.

Passwords use salted scrypt (`N=2^17`, `r=8`, `p=1`), following
[OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). At most two hashes run
concurrently per process. Sessions use random tokens; only SHA-256 token hashes
are stored in SQLite. Cookies are HttpOnly and SameSite=Strict, expire after
24 hours, rotate on login, and are revoked on logout. API responses use
`Cache-Control: no-store`.

Mutating API requests require `X-JobTrack: 1`; browser requests with a foreign
Origin are rejected. The client sends the header automatically. Scripts using
the API must send it too. Login and registration share a persistent limit of
20 attempts per client IP per 60-second window; exceeded limits return 429.

For HTTPS hosting, set `JOBTRACK_SECURE_COOKIE=1`, use persistent database
storage, and configure the reverse proxy so the app receives the correct
scheme and client address. Trust forwarded headers only from your proxy.
Secure cookies should remain disabled only for local HTTP development.
Password reset, email verification, and account deletion remain future work.

## Data and configuration

The default database is `.data/jobtrack.sqlite3`. To run with a separate local
database:

```bash
JOBTRACK_DB=.data/demo.sqlite3 bash scripts/run.sh
```

Tests pass an isolated database path to `create_app(db_path)` and do not use
personal application records. Database initialization adds account/session tables and an `owner_id` column
to existing application tables. Unowned records remain preserved and private
until assigned with `scripts/claim_legacy.py`; initialization is repeatable.
General versioned schema migrations remain planned.

## Verify a change

```bash
bash scripts/test.sh
node --check web/app.js
```

The GitHub Actions workflow is configured to run Python tests and JavaScript
syntax and frontend authentication checks on pushes and pull requests. Locally, setup and the test script
have passed all 27 API tests, and the JavaScript syntax check has passed.

## Making changes

See `ROADMAP.md` for planned features and acceptance criteria.
Keep changes focused, test the behavior, and use
commit messages that describe the change.

Example: `feat: export filtered applications as CSV`.

Keep routes in `api.py` and persistence in `store.py`. SQL values use parameters;
updated column names must come from an allowlist. Render record text with
`textContent` instead of interpolating it into `innerHTML`. Preserve the API
when changing the browser client, or document an intentional API change.

Add tests for changed behavior and boundary cases. Run the checks above before
committing. Keep `.data/`, `.venv/`, `.env` files, and credentials out of Git.

## Project credits

The initial implementation was prepared with Codex assistance.
