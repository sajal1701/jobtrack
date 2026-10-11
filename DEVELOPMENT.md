# Developing JobTrack

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
| POST | `/api/applications` | Create an application |
| GET | `/api/applications/{id}` | Read one application |
| PATCH | `/api/applications/{id}` | Update stage, notes, or follow-up date |
| DELETE | `/api/applications/{id}` | Delete one application |
| GET | `/api/stats` | Counts for all applications |

## Verify a change

```bash
bash scripts/test.sh
node --check web/app.js
```

The GitHub Actions workflow is configured to run Python tests and JavaScript
syntax checks on pushes and pull requests. Locally, setup and the test script
have passed all 12 API tests, and the JavaScript syntax check has passed.

## Development

See `ROADMAP.md` for planned features and acceptance criteria.
Keep changes focused, test the behavior, and use
commit messages that describe the change.

Example: `feat: export filtered applications as CSV`.

The initial implementation was prepared with Codex assistance.
