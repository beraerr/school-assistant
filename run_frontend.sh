#!/bin/bash
set -e

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

exec streamlit run frontend/app.py --server.port="${PORT:-8501}" --server.address=0.0.0.0 --server.headless=true
