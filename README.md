# CASTLE QA Studio

**AI Video Understanding & Grounded Question-Answering for Whodunnit Annotation Assistance**

CASTLE QA Studio is an annotation assistance platform designed to extract, inspect, and evaluate event timelines and question-answering pairs from long video recordings. It pairs a **FastAPI** backend, an asynchronous **worker queue** running **Qwen2.5-VL**, and a modern **ReactJS + Vite + TypeScript** frontend.

---

## 1. System Capabilities

- **Local-First Privacy**: Original 1-hour CASTLE recordings (~1.28 GB) remain on the annotator's computer. Only short, user-selected clips (<= 120s, <= 200MB) are uploaded to the backend.
- **Qwen2.5-VL Video Understanding**: Extracts chronological observable events with dual timestamp intervals (`start_seconds`, `end_seconds` and source-relative `source_start_seconds`, `source_end_seconds`), actor identification, actions, objects, targets, and concise factual summaries.
- **Grounded Video Question Answering (Video QA)**: Annotators ask natural language questions about video content and receive answers grounded with:
  - Temporal video evidence intervals.
  - Observability status (distinguishing directly observable facts from uncertain interpretations).
  - Evidence-matching confidence scores.
  - One-click timeline seeking directly to the supporting evidence in the video player.
- **Human Annotation Review Loop**: Annotators review, edit, accept, or reject AI-extracted events and generated questions.
- **Whodunnit Export Adapter**: Exports human-verified annotations into Whodunnit-compatible JSON and CSV formats with candidate distractors derived from scene actors.
- **Temporary Storage Lifecycle**: 24-hour meaningful inactivity TTL, cross-process stream lease tracking, 30-second active upload reservation refreshing, and persistent library saving.

---

## 2. Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │    ReactJS Frontend (Vite + TS)        │
                      │  - Video player with interval scrubber │
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
                      │   Inference Worker (Mock or Qwen GPU)  │
                      │  - Background heartbeat thread         │
                      │  - Video understanding analysis        │
                      │  - Grounded question generation        │
                      └────────────────────────────────────────┘
```

---

## 3. Quick Start (Local Laptop Development)

Local CPU testing and development can be performed on Windows, macOS, or Linux without an NVIDIA GPU using the built-in mock and template engines.

### 1. Prerequisites & Installation
- Python >= 3.10
- Node.js >= 18.x & npm
- FFmpeg on system `PATH`

From repository root:
```powershell
# Install backend package with API and dev dependencies
python -m pip install -e "./backend[api,dev]"

# Initialize database schema
python -m alembic -c backend/alembic.ini upgrade head

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Start Backend & Mock Worker
```powershell
# In terminal 1 (FastAPI backend):
python -m uvicorn castle_qa.api.main:create_app --factory --host 127.0.0.1 --port 8000

# In terminal 2 (Mock Worker):
python -m castle_qa.workers.entrypoint --mock
```

### 3. Start Frontend
```powershell
# In terminal 3 (Vite Frontend):
cd frontend
npm install
npm run dev
# Open http://localhost:3000 in your browser
```

### 4. Run Pre-Flight Diagnostics
```powershell
python -m castle_qa.deployment.readiness_check
```

---

## 4. Documentation Index

Detailed engineering documentation is organized in the `docs/` directory:

- [docs/architecture.md](file:///d:/DCU-Internship/castle-question-generation/docs/architecture.md): Technical architecture, data flows, dual timestamp mapping, and storage lifecycles.
- [docs/DEVELOPMENT.md](file:///d:/DCU-Internship/castle-question-generation/docs/DEVELOPMENT.md): Detailed local development guide, setup instructions, and troubleshooting.
- [docs/LAB_GPU_DEPLOYMENT.md](file:///d:/DCU-Internship/castle-question-generation/docs/LAB_GPU_DEPLOYMENT.md): Step-by-step handover and deployment guide for the NVIDIA GPU lab PC.
- [docs/TESTING.md](file:///d:/DCU-Internship/castle-question-generation/docs/TESTING.md): Comprehensive test suite guide (181 backend pytest tests, 74 frontend tests, 15 Playwright E2E tests).
- [docs/API.md](file:///d:/DCU-Internship/castle-question-generation/docs/API.md): Authoritative REST API inventory based on OpenAPI route registration.
- [docs/ANNOTATION_PROVENANCE.md](file:///d:/DCU-Internship/castle-question-generation/docs/ANNOTATION_PROVENANCE.md): Inference provenance (mock vs real), heuristic QA scores, and review statuses.

---

## 5. Running Tests

```powershell
# Backend Pytest Suite (181 tests)
python -m pytest backend/tests -v

# Frontend Unit & Component Tests (74 tests)
npm --prefix frontend test

# Browser End-to-End Tests (Playwright on Microsoft Edge - 15 tests)
npm --prefix frontend run test:e2e

# Production Frontend Build
npm --prefix frontend run build
```

---

## 6. Important Operational Limitations

1. **Current Environment**: Development and verification are conducted on a Windows laptop without an NVIDIA CUDA GPU. Real Qwen2.5-VL inference is prepared for deployment on a dedicated lab PC (Task 8).
2. **QA Confidence Scoring**: Confidence scores displayed in Grounded QA are **heuristic evidence-matching metrics**, not calibrated Bayesian probabilities of answer correctness.
3. **Whodunnit Compatibility**: Exports use a research-compatible adapter with candidate distractor generation, not an officially certified schema.
4. **Frame Sampling Baseline**: The system operates at a verified **1.0 FPS** baseline. Experimental 2.0 FPS sampling is supported via configuration (`VIDEO_FPS=2.0`).
