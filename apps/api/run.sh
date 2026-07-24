#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — paste your Neon pooled DATABASE_URL before continuing."
fi

echo "Running migrations..."
alembic upgrade head

echo "Starting API at http://127.0.0.1:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
