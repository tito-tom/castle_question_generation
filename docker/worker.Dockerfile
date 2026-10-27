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

# Install the API and GPU dependency sets. requirements-gpu.txt pins the
# CUDA-enabled PyTorch/Torchvision pair and compatible Transformers versions.
COPY requirements-api.txt .
COPY requirements-gpu.txt .

RUN python -m pip install --no-cache-dir \
    -r requirements-api.txt \
    -r requirements-gpu.txt

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

# Install package in container
RUN python -m pip install --no-cache-dir -e .

CMD ["python", "-m", "castle_qa.workers.entrypoint", "--poll-interval", "2.0"]
