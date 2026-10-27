# CASTLE QA Studio — Local Laptop Development Guide

This guide covers setting up, running, testing, and debugging CASTLE QA Studio on a local development laptop (Windows 11 / 10 / macOS / Linux) using CPU-only mock inference.

---

## 1. Prerequisites

Before starting, ensure the following utilities are installed and available on your system `PATH`:

| Tool | Recommended Version | Verification Command | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10 or 3.11 | `python --version` | Miniconda or standard Python |
| **Node.js** | 20.x LTS (>= 18.x) | `node -v` | Installed with `npm` |
| **npm** | 10.x (>= 9.x) | `npm -v` | Node package manager |
| **FFmpeg** | >= 5.0 (Recommended 7.x) | `ffmpeg -version` | Must include `ffprobe` |
| **Microsoft Edge** or **Chrome** | Latest stable | (Default installed) | Required for Playwright E2E tests |

---

## 2. Initial Setup

### 2.1 Backend Setup
Open a terminal (PowerShell or Bash) in the repository root:
```powershell
# Option A: Install from repository root (recommended)
python -m pip install -e "./backend[api,dev]"

# Option B: Navigate to backend directory first
cd backend
python -m pip install -e ".[api,dev]"
cd ..

# Initialize database migrations (from repo root or backend)
# From repo root:
python -m alembic -c backend/alembic.ini upgrade head
# Or from backend directory:
# cd backend && alembic upgrade head
```

> [!NOTE]
> **Repository Package Layout**: The package definition file `pyproject.toml` resides inside `backend/` and targets `where = ["src"]`. Running `pip install -e .` directly from the repository root without `./backend` will fail because `pyproject.toml` is not located in the repository root.

### 2.2 Frontend Setup
In a separate terminal or the same terminal:
```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install npm dependencies
npm install
```

---

## 3. Running the Development Stack

To run the application locally on your laptop, start three lightweight processes.

### Terminal 1: FastAPI Backend
```powershell
python -m uvicorn castle_qa.api.main:app --host 127.0.0.1 --port 8000
```
- Health check URL: `http://127.0.0.1:8000/api/v1/health`
- Interactive Swagger docs: `http://127.0.0.1:8000/docs`

### Terminal 2: Background Inference Worker (CPU Mock Mode)
```powershell
python -m castle_qa.workers.entrypoint --mock
```
- Runs in deterministic mock simulation mode.
- Does **NOT** require NVIDIA GPU, CUDA runtime, or Qwen model weights.
- Processes queued jobs with deterministic mock results; elapsed time depends on the host and workload.

### Terminal 3: React + Vite Frontend
```powershell
npm --prefix frontend run dev
```
- UI URL: `http://localhost:3000`
- Proxies `/api/v1` requests to FastAPI on port 8000.

---

## 4. Pre-Flight Diagnostic Check

Verify that all local storage directories, Python dependencies, and FFmpeg tools are healthy by running the Deployment Readiness Checker:
```powershell
python -m castle_qa.deployment.readiness_check
```
**Expected Output on Laptop**:
```
OVERALL READINESS: READY FOR DEVELOPMENT (CPU mock environment ready, zero GPU required)
Exit Code: 0
```

---

## 5. Running the Test Suites

### 5.1 Backend Pytest Suite
```powershell
python -m pytest backend/tests -v
```
- Runs the backend unit, integration, and verification tests.
- All tests execute with isolated temporary directories and mock inference engines.

### 5.2 Frontend Unit and Component Tests
```powershell
npm --prefix frontend test
```
- Runs the Node and Vitest test suites.
- Verifies local video isolation, object URL revocation, criteria handling, question editing, and timeline rendering.

### 5.3 Playwright Browser End-to-End Suite
Ensure the Backend (port 8000), Mock Worker, and Frontend (port 3000) are running, then run:
```powershell
npm --prefix frontend run test:e2e
```
- Runs the configured browser end-to-end scenarios.

### 5.4 Production Frontend Build
```powershell
npm --prefix frontend run build
```
- Runs TypeScript compiler (`tsc`) and Vite asset bundling.
- Verifies that no type errors exist and bundles the production output into `frontend/dist/`.

---

## 6. Stopping Development Services Safely

If background services are running in PowerShell, stop them via `Ctrl+C` in their respective windows, or check active ports:
```powershell
# Check which processes are using ports 8000 and 3000
Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess, State

# Stop a process by PID if needed
Stop-Process -Id <PID> -Force
```

---

## 7. Common Development Issues and Solutions

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `FileNotFoundError: ffmpeg` | FFmpeg is not installed or not on `PATH` | Install FFmpeg and add the `bin/` directory to your system environment variables. |
| `TypeError: Object of type MagicMock is not JSON serializable` | Mocking `datetime` globally in tests | Pass a custom `now_fn` to `TemporarySessionService` rather than patching standard library modules. |
| `413 Request Entity Too Large` during upload | Clip exceeds configured maximum request size | Keep extracted clips under 1 GB, or adjust `CASTLE_MAX_CLIP_SIZE_BYTES` and `CASTLE_MAX_REQUEST_SIZE_BYTES` together. |
| `403 Forbidden` on stream lease renewal | Clip is temporary and request lacks valid session token | Provide `X-Session-Token` header or `?token=<session_token>` query parameter. |
| Playwright tests fail with `ECONNREFUSED` | Vite or FastAPI is not running | Ensure both `localhost:3000` (Vite) and `127.0.0.1:8000` (FastAPI) are active before launching `test:e2e`. |

