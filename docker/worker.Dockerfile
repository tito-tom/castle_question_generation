# ==========================================
# CASTLE QA Studio - GPU Worker Container
# Targets NVIDIA CUDA (e.g. RTX 5090) on Ubuntu
# ==========================================

FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install required Python packages for worker, queue, and Qwen
COPY requirements-api.txt .
COPY requirements-gpu.txt .

RUN python -m pip install --no-cache-dir \
    sqlalchemy>=2.0 \
    alembic>=1.13 \
    pydantic>=2.7 \
    python-dotenv>=1.0 \
    transformers>=4.48 \
    accelerate>=1.0 \
    av>=14 \
    Pillow>=10 \
    torchvision

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
