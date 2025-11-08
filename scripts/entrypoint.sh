#!/usr/bin/env bash
set -euo pipefail

# Ensure Python can import top-level packages (e.g., ml_models)
export PYTHONPATH="/app/entrenamiento_niñeravirtual2:${PYTHONPATH:-}"

# Apply database migrations (Postgres if DATABASE_URL is set; otherwise SQLite)
python entrenamiento_niñeravirtual2/ninera_virtual/manage.py migrate --noinput

# Ensure media and legacy DB locations exist
mkdir -p "$(dirname "${LEGACY_DB_PATH:-/data/ninera_virtual.db}")" "$MEDIA_ROOT"

exec gunicorn ninera_virtual.wsgi:application \
  --chdir entrenamiento_niñeravirtual2 \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WEB_CONCURRENCY:-2} \
  --timeout 120
