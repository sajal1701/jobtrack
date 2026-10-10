#!/usr/bin/env bash
set -euo pipefail
project_path="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_path"
python_bin="${PYTHON_BIN:-python3}"
"$python_bin" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required"'
if [ ! -d .venv ]; then "$python_bin" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
printf '\nSetup complete. Start this project with: bash scripts/run.sh\n'
