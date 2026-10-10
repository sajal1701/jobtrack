# JobTrack backlog

Choose one item or one useful slice per session. A larger item may take multiple
sessions; every commit should capture real progress. Checked items describe the
starter, not fabricated development history.

- [x] J00 — Local tracker with persistence, search, stage changes, validation,
  browser UI, API tests, and a CI configuration.
- [ ] J01 — CSV export. Add an export endpoint and a browser download button.
  Acceptance: stage/search filters match the list endpoint; quotes and newlines
  survive export; add an API test with at least two different applications.
- [ ] J02 — Edit company, role, URL, notes, and follow-up date in the browser.
  Acceptance: partial updates preserve omitted values and validation remains
  consistent with creation; test a failed edit and a successful one.
- [ ] J03 — Browser pagination. Add next/previous controls and matching counts.
  Acceptance: more than 100 records can be navigated without losing filters;
  disabled buttons and empty pages behave correctly.
- [ ] J04 — Follow-up view. Show due and upcoming applications using an explicit
  local date. Acceptance: closed applications are excluded; test today, tomorrow,
  no date, and a past date.
- [ ] J05 — Application activity history. Store stage-change events.
  Acceptance: transitions have timestamps and old/new values; history survives
  restart and is displayed in an application detail view.
- [ ] J06 — CSV import preview. Validate imported rows before saving.
  Acceptance: show row errors, reject invalid URLs/dates, and define an explicit
  duplicate policy; importing the same file twice has documented behavior.
- [ ] J07 — Introduce a React + TypeScript client in small slices.
  Acceptance: the existing application list and add flow use the same API;
  record setup steps and preserve the working starter until parity is verified.
- [ ] J08 — Add client tests for create, edit, stage changes, and API errors.
  Acceptance: a failed request leaves the visible state consistent and the error
  is accessible; frontend checks run in CI.
- [ ] J09 — Introduce versioned database migrations and PostgreSQL support.
  Acceptance: existing records survive migration; integration tests cover both
  the default local database and the PostgreSQL configuration.
- [ ] J10 — Implement registration and login as a separate milestone.
  Acceptance: stored passwords are hashed, invalid credentials fail, and logout
  behavior is documented. Split this into reviewable changes.
- [ ] J11 — Scope application data to the authenticated owner.
  Acceptance: one user cannot read, edit, or delete another user's application;
  include explicit cross-user API tests before any public deployment.
- [ ] J12 — Add a status board and accessible loading/empty/error states.
  Acceptance: moving an application updates the API; keyboard operation works;
  failed updates can be retried without duplicating records.
- [ ] J13 — Add a container and a documented deployment configuration.
  Acceptance: a fresh environment can run the app and database; health checks and
  persistence work. Choose hosting separately and verify production settings.
- [ ] J14 — Finish the portfolio presentation.
  Acceptance: README has real screenshots, architecture, verified setup, known
  limitations, and a short demo; any performance claims name the measurement.
