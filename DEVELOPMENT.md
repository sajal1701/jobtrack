# Developing JobTrack

Start with [the user guide](README.md) to install and run the app. This document
covers the code structure, API behavior, and checks for contributors.

## Project structure

| Path | Responsibility |
| --- | --- |
| `jobtrack/api.py` | FastAPI routes, request validation, and static file serving |
| `jobtrack/store.py` | SQLite schema, queries, and transactions |
| `web/` | Browser interface, styles, and application state |
| `tests/test_api.py` | API tests using temporary databases |
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
| PATCH | `/api/applications/{id}` | Update stage, notes, or follow-up date |
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
`status` and `notes` cannot be null. An empty patch returns 400, invalid input
returns 422, and missing records return 404. Company, role, and URL cannot yet
be changed through PATCH.

## Data and configuration

The default database is `.data/jobtrack.sqlite3`. To run with a separate local
database:

```bash
JOBTRACK_DB=.data/demo.sqlite3 bash scripts/run.sh
```

Tests pass an isolated database path to `create_app(db_path)` and do not use
personal application records. Database initialization creates the table if it
does not exist; versioned schema migrations are still planned.

## Verify a change

```bash
bash scripts/test.sh
node --check web/app.js
```

The GitHub Actions workflow is configured to run Python tests and JavaScript
syntax checks on pushes and pull requests. Locally, setup and the test script
have passed all 15 API tests, and the JavaScript syntax check has passed.

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
