#!/usr/bin/env bash

set -o errexit

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -m pip install -r requirements.txt
"$PYTHON_BIN" manage.py collectstatic --no-input
