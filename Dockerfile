FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies for opencv/ultralytics/torch and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY entrenamiento_niñeravirtual2/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install -r /app/requirements.txt

# Copy application source
COPY entrenamiento_niñeravirtual2 /app/entrenamiento_niñeravirtual2

# Include model weights from common locations (present in this repo)
RUN mkdir -p /app/ml_models
COPY entrenamiento_niñeravirtual2/ml_models /app/entrenamiento_niñeravirtual2/ml_models
COPY yolov8s.pt /app/ml_models/
COPY NiñeraV.pt /app/ml_models/

# Runtime dirs and sensible defaults for container
RUN mkdir -p /data/media
ENV DJANGO_DEBUG=false \
    MEDIA_ROOT=/data/media \
    LEGACY_DB_PATH=/data/ninera_virtual.db \
    PORT=8000

# Collect static files at build time (does not require DB)
RUN python entrenamiento_niñeravirtual2/ninera_virtual/manage.py collectstatic --noinput

# Entrypoint: run migrations and start Gunicorn
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
CMD ["/entrypoint.sh"]

