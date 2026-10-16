
# ==========================================
# CASTLE QA Studio - FastAPI Backend
# ==========================================

# 1. Use a lightweight Python image.
FROM python:3.10-slim-bookworm

# 2. Configure Python for containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Set the application directory.
WORKDIR /app

# 4. Install CPU-only API dependencies.
COPY requirements-api.txt .

RUN python -m pip install --no-cache-dir \
    -r requirements-api.txt

# 5. Create a non-root application user
#    and writable data directories.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/analysis \
                 /app/data/questions/api_template \
    && chown -R appuser:appuser /app/data

# 6. Copy the Python application.
COPY --chown=appuser:appuser src/ ./src/

# 7. Run the API as a non-root user.
USER appuser

# 8. Document the API port.
EXPOSE 8000

# 9. Check whether FastAPI is responding.
HEALTHCHECK --interval=30s --timeout=5s \
    --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

# 10. Start FastAPI.
CMD ["python", "-m", "uvicorn", \
     "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
