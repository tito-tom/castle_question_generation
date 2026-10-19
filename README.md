# CASTLE QA Studio

**AI Video Understanding & Grounded Question-Answering for Whodunnit Annotation Assistance**

CASTLE QA Studio is an end-to-end platform designed to assist human annotators working on the Whodunnit video understanding benchmark. It pairs a **FastAPI** backend, an asynchronous **GPU inference queue** running **Qwen2.5-VL**, and a modern **ReactJS + Vite + TypeScript** frontend.

---

## 1. System Capabilities

- **Video Ingestion & Storage**: Safe upload, duration and size validation, atomic writes, FFprobe metadata extraction, and subclip extraction.
- **Qwen2.5-VL Video Understanding**: Extracts chronological observable events with precise timestamp intervals (`start_seconds`, `end_seconds`), actor identification, actions, objects, targets, and concise factual summaries.
- **Grounded Video Question Answering (Video QA)**: Users ask questions about video content and receive grounded answers with:
  - Temporal video evidence intervals (`start_seconds`, `end_seconds`).
  - Observability status (distinguishing directly observable facts from uncertain interpretations).
  - Confidence scoring.
  - One-click timeline seeking directly to the supporting evidence in the video player.
- **Human Annotation Review Loop**: Annotators review, edit, accept, or reject AI-extracted events and generated questions.
- **Whodunnit Export Adapter**: Exports human-verified annotations into Whodunnit-compatible JSON and CSV formats with candidate distractors derived from other scene actors.
- **Worker Crash Recovery**: Heartbeat tracking, atomic job claims, retry counts, and automatic stale job recovery without duplicate results.

---

## 2. Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │    ReactJS Frontend (Vite + TS)        │
                      │  - Video player with evidence scrubber │
                      │  - Chronological event timeline        │
                      │  - Grounded Video QA query panel       │
                      │  - Whodunnit review & export modal     │
                      └──────────────────┬─────────────────────┘
                                         │ (HTTP / JSON / Video Stream)
                                         ▼
                      ┌────────────────────────────────────────┐
                      │         FastAPI Backend (Port 8000)    │
                      │  - /api/v1/videos (upload, stream)     │
                      │  - /api/v1/analyses (view events)      │
                      │  - /api/v1/jobs (async job queue)      │
                      │  - /api/v1/qa (grounded video QA)      │
                      │  - /api/v1/annotations (review/export) │
                      └──────────────────┬─────────────────────┘
                                         │
             ┌───────────────────────────┴───────────────────────────┐
             ▼                                                       ▼
┌─────────────────────────────┐                         ┌─────────────────────────────┐
│   SQLite Job Queue & DB     │                         │   Storage & Repositories    │
│  - Claim tokens & worker IDs│                         │  - data/videos (raw video)  │
│  - Heartbeat tracking       │                         │  - data/analysis (JSON)     │
│  - Stale job auto-recovery  │                         │  - data/reviews (sessions)  │
└────────────┬────────────────┘                         └──────────────┬──────────────┘
             │                                                         │
             └───────────────────────────┬─────────────────────────────┘
                                         ▼
                      ┌────────────────────────────────────────┐
                      │     GPU Inference Worker (Qwen2.5-VL)  │
                      │  - Background heartbeat thread         │
                      │  - Video understanding analysis        │
                      │  - Grounded question generation        │
                      └────────────────────────────────────────┘
```

---

## 3. Local Development (Windows / CPU)

Local CPU testing and development can be performed on Windows without an NVIDIA GPU using the built-in mock and template engines.

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- FFmpeg installed and available on `PATH`

### 1. Backend Setup
```powershell
# Navigate to backend and install in editable mode
cd backend
pip install -e ".[api,dev]"

# Run database migrations
alembic upgrade head

# Start FastAPI backend
uvicorn castle_qa.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start Worker (Mock Mode for CPU)
```powershell
cd backend
python -m castle_qa.workers.entrypoint --poll-interval 2.0 --mock-models
```

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
# Accessible at http://localhost:3000
```

### 4. Running Tests
```powershell
# Run the complete test suite (106 tests)
cd backend
pytest -v
```

---

## 4. Production Deployment (Ubuntu + NVIDIA RTX 5090)

The multi-container orchestration is defined in `compose.yaml`.

### 1. Build and Run
```bash
docker compose up --build -d
```

### 2. Services Started
- **`castle-qa-api`**: FastAPI backend listening on port `8000`.
- **`castle-qa-worker`**: Qwen2.5-VL GPU worker with NVIDIA container runtime reservation (`nvidia.com/gpu: all`).
- **`castle-qa-frontend`**: Nginx serving the compiled ReactJS application on port `3000` with reverse proxying to the backend.

---

## 5. Configuration & Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CASTLE_JOB_DB_PATH` | `data/jobs/jobs.sqlite3` | SQLite path for inference job queue |
| `CASTLE_ANALYSIS_DIR` | `data/analysis` | Directory storing structured `VideoAnalysis` JSON files |
| `CASTLE_VIDEO_STORAGE_DIR` | `data/videos` | Storage location for ingested video files |
| `CASTLE_CLIPS_DIR` | `data/clips` | Directory for extracted video subclips |
| `CASTLE_REVIEWS_DIR` | `data/reviews` | Storage for human annotation review sessions |
| `VIDEO_UNDERSTANDING_MODE` | `real` (or `mock`) | Toggle between Qwen2.5-VL GPU inference and mock service |
| `VIDEO_MODEL_NAME` | `Qwen/Qwen2.5-VL-7B-Instruct` | Hugging Face model checkpoint for video understanding |
| `VIDEO_FPS` | `2.0` | Sampling frame rate for video understanding |
| `MAX_NEW_TOKENS` | `1024` | Maximum tokens generated during VLM inference |

---

## 6. Whodunnit Annotation Adapter Notes

As per system specifications, exact field schemas for the Whodunnit platform are decoupled using the `WhodunnitExportAdapter` (`src/services/whodunnit_export_adapter.py`). 

The current configuration exports `whodunnit_v1_draft`:
- **Events**: Start/end timestamps, actor labels, normalized actions, target objects, and verification metadata.
- **QA Pairs**: Who questions, ground-truth actors, and automatically computed **candidate distractors** (all other distinct actors appearing in the scene).
- **Formats**: Available as both structured JSON and tabular CSV.