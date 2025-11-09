#!/usr/bin/env bash
set -euo pipefail

# Ensure Python can import top-level packages (e.g., ml_models)
export PYTHONPATH="/app/entrenamiento_niñeravirtual2:/app/entrenamiento_niñeravirtual2/ninera_virtual:${PYTHONPATH:-}"
# Limit math/BLAS threads to reduce RAM/CPU usage on small instances
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-1}
export TORCH_NUM_THREADS=${TORCH_NUM_THREADS:-1}

# Ensure media and DB locations exist
mkdir -p "$(dirname "${LEGACY_DB_PATH:-/data/ninera_virtual.db}")" "$MEDIA_ROOT"

# Run migrations (idempotent and fast); ensures tables exist
python entrenamiento_niñeravirtual2/ninera_virtual/manage.py migrate --noinput

# Prefer ASGI server (daphne) to support WebSockets
cd entrenamiento_niñeravirtual2/ninera_virtual
exec daphne -b 0.0.0.0 -p ${PORT:-8000} ninera_virtual.asgi:application
