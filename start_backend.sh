#!/bin/bash
# Start backend with correct PYTHONPATH

cd "$(dirname "$0")"

export PYTHONPATH="$(pwd):$PYTHONPATH"

source venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
