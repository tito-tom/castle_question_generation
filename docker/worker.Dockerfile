# ==========================================
# CASTLE QA Studio - GPU Worker Container
# Targets NVIDIA CUDA (e.g. RTX 5090) on Ubuntu
# ==========================================

FROM pytorch/pytorch:2.13.0-cuda13.0-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /app/data/analysis \
             /app/data/questions/api_template \
             /app/data/jobs \
             /app/data/videos \
             /app/data/clips \
             /app/data/reviews

# Copy application code, prompts, and database migrations from backend/
COPY backend/src/ ./src/
COPY backend/prompts/ ./prompts/
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic/ ./alembic/
COPY backend/pyproject.toml ./pyproject.toml

# Install the backend and pinned CUDA stack from pyproject.toml.
# Include development tools to retain the worker's existing pytest installation.
RUN python -m pip install --break-system-packages --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cu130 \
    -e ".[gpu,dev]"

CMD ["python", "-m", "castle_qa.workers.entrypoint", "--poll-interval", "2.0"]
