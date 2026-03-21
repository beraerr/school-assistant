#!/bin/bash
# Run FastAPI backend server

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
