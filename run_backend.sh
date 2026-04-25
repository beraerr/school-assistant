#!/bin/bash
set -e

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
