# ==========================================
# CASTLE QA Studio - FastAPI Backend
# ==========================================

FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies including ffmpeg for video probing & clipping
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only API dependencies
COPY requirements-api.txt .
RUN python -m pip install --no-cache-dir -r requirements-api.txt

# Create application user and writable data directories
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/analysis \
                 /app/data/questions/api_template \
                 /app/data/jobs \
                 /app/data/videos \
                 /app/data/clips \
                 /app/data/reviews \
    && chown -R appuser:appuser /app/data

# Copy source code, prompts, and database migrations
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser prompts/ ./prompts/
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser alembic/ ./alembic/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
    --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", \
     "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
