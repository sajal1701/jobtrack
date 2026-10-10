# Working in JobTrack

## Goal

Help Sajal build a portfolio project through small, explainable improvements.
This repository is a working starter, not a finished multi-user product.

## Each session

1. Read README.md and ROADMAP.md; inspect the current files and git status.
2. Choose one incomplete backlog item. If it is too large, implement one useful
   slice and leave the remaining acceptance criteria open.
3. Explain the expected behavior and the design choice briefly.
4. Make a focused change. Add meaningful tests for behavior, bugs, or boundaries.
5. Run the relevant checks and report the exact result. Mark a task complete only
   when its acceptance criteria are met.
6. Show the diff summary and suggest a descriptive commit message. Commit/push
   when requested by the user; preserve unrelated working changes.
7. Ask Sajal to explain one design decision and one edge case from the change.

## Conventions

- Python 3.11+; FastAPI routes stay in jobtrack/api.py, persistence in store.py.
- SQLite queries use parameters for values; column updates use an allowlist.
- Create API apps with isolated database paths in tests.
- UI text derived from records uses textContent, not interpolated innerHTML.
- Preserve the existing API during frontend migrations, or document the change.
- Never commit .data, .env, .venv, personal application records, or API keys.
- Do not manufacture empty commits, backdate activity, or claim unmeasured impact.
- Prefer small changes that Sajal can explain over broad rewrites.

## Checks

After setup: `bash scripts/test.sh` and `node --check web/app.js`.
During bootstrap: `python3 -m unittest discover -s tests -v`.
