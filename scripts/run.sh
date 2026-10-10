#!/usr/bin/env bash
set -euo pipefail
project_path="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_path"
if [ ! -x .venv/bin/python ]; then printf 'Run bash scripts/setup.sh first.\n' >&2; exit 1; fi
exec .venv/bin/python -m uvicorn jobtrack.api:app --host 127.0.0.1 --port 8010 --reload
