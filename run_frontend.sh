#!/bin/bash
# Run Streamlit frontend

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

streamlit run frontend/app.py
