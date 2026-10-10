# JobTrack

A local-first job application tracker with a FastAPI backend, SQLite persistence,
and a small browser interface. Track opportunities, change stages, filter records,
and record your next follow-up.

## Run on your Mac

Requires Python 3.11 or newer. In Terminal, enter the `jobtrack` folder:

```bash
bash scripts/setup.sh
bash scripts/run.sh
```

Open http://127.0.0.1:8010. API documentation: http://127.0.0.1:8010/docs.
Stop the server with Control+C. Setup creates a project-specific `.venv`.
Application data is stored in `.data/jobtrack.sqlite3`, which Git ignores.
Set `JOBTRACK_DB` to use a different database file.

## What works today

- Create, list, read, update, and delete applications through the REST API.
- Add applications and change stages in the browser.
- Store company, role, URL, notes, status, and an optional follow-up date.
- Filter by stage and search company or role; search treats `%` and `_` literally.
- View total applications, applied applications, interviews, and offers.
- Validate blank fields, status values, dates, and link schemes.
- Use parameterized SQL and scoped transactions.
- Run 12 API tests against isolated temporary databases.

This is a single-user local starter. Authentication, multi-user ownership,
PostgreSQL, a React client, imports, and production deployment are backlog items.
The browser currently displays up to 100 matching applications; the API has
`limit` and `offset` parameters. Statistics cover all stored applications.

## Architecture

`web/` is the browser client. `jobtrack/api.py` validates HTTP input and maps
missing records to HTTP errors. `jobtrack/store.py` owns SQLite operations.
`create_app(db_path)` makes it possible to test persistence without touching
personal data. The server serves the UI and API from the same origin.

The starter intentionally keeps the client small. A later React migration can
preserve the API while adding component-based state and frontend tests.

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

The GitHub Actions workflow runs Python tests and JavaScript syntax checks on
pushes and pull requests. It has not run on GitHub until this repo is published.

## Develop with Codex

Open this folder as a local project in Codex. Read `AGENTS.md` and `ROADMAP.md`.
Start with J01. Work on one small outcome per session, review the diff, then make
a commit that describes the behavior you changed.

Example: `feat: export filtered applications as CSV`.

Starter code was prepared with Codex assistance. Extend and explain each change
yourself before presenting the project in an interview.
