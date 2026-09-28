#!/usr/bin/env bash
# Runs the CAFS backend (FastAPI :8000) and frontend (Next.js :3000) together. Ctrl+C stops both.
ROOT="$(cd "$(dirname "$0")" && pwd)"
trap 'kill 0' INT TERM EXIT
(cd "$ROOT/backend" && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000) &
(cd "$ROOT/frontend" && npm run dev -- --port 3000) &
wait
