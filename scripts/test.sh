#!/usr/bin/env bash
set -euo pipefail
project_path="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_path"
.venv/bin/python -m unittest discover -s tests -v
