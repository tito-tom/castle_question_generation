# CASTLE QA Studio

CASTLE QA Studio turns a selected video interval into a readable event timeline, then generates evidence-grounded question suggestions for use by annotators in other tools.

## What it does

- Opens and previews a video in the browser. The original recording stays on the user's computer.
- Extracts one continuous interval, up to 10 minutes, and uploads only that clip for analysis.
- Shows a chronological video summary and event timeline with source timestamps.
- Generates question suggestions from retained video-understanding evidence. Optional criteria guide question style and event selection; they cannot add unsupported video facts.
- Supports CPU mock processing for development and local Qwen2.5-VL inference on a configured NVIDIA GPU worker.

The main workspace has two result tabs: **Video Understanding** and **Generate Questions**. The backend retains additional API routes for compatibility and existing data; annotation review and video chat are not part of the primary user workflow.

## Architecture

~~~mermaid
flowchart LR
    Browser[React and Vite app] -->|selected clip and API requests| API[FastAPI API]
    API -->|job records| DB[(SQLite job queue)]
    Worker[Mock or local Qwen worker] -->|claims and updates jobs| DB
    Worker -->|analysis and question records| Storage[(JSON data stores)]
    API --> Storage
~~~

The frontend is organized by user-facing feature. The backend follows a layered structure: API routes and schemas, application workflows, domain models, services, repositories, and a separate inference worker.

New to this stack? Start with [Learn the codebase from Python and OOP](docs/learning/README.md), covering technologies, architecture, storage, route contracts, workers, Qwen, testing, and a walkthrough of the frontend entry files.

## Run with Docker

### CPU development with mock inference

~~~bash
docker compose up -d --build
docker compose exec api python -m alembic -c /app/alembic.ini upgrade head
~~~

Open [http://localhost:3000](http://localhost:3000). The API health endpoint is [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health).

### NVIDIA GPU worker

On a host with Docker's NVIDIA Container Toolkit configured:

~~~bash
docker compose -f compose.yaml -f compose.gpu.yaml up -d --build
docker compose -f compose.yaml -f compose.gpu.yaml exec api python -m alembic -c /app/alembic.ini upgrade head
~~~

The GPU override selects real inference and keeps the Hugging Face model cache in a named Docker volume. The first worker start downloads model files; later starts reuse that cache. See [docs/LAB_GPU_DEPLOYMENT.md](docs/LAB_GPU_DEPLOYMENT.md) for setup and troubleshooting.

## Develop locally

Prerequisites: Python 3.10+, Node.js 18+, npm, and FFmpeg with ffprobe available on PATH.

~~~bash
python -m pip install -e "./backend[api,dev]"
python -m alembic -c backend/alembic.ini upgrade head
npm --prefix frontend install
~~~

Run the API, mock worker, and frontend in separate terminals from the repository root:

~~~bash
python -m uvicorn castle_qa.api.main:app --host 127.0.0.1 --port 8000
python -m castle_qa.workers.entrypoint --mock
npm --prefix frontend run dev
~~~

## Repository map

~~~text
backend/src/castle_qa/
  api/             HTTP routes, schemas, dependencies, middleware
  application/     Video and question workflows
  domain/          Analysis, event, job, and criteria models
  infrastructure/  SQLite and file-backed repositories
  services/        Video processing, inference, and generation
  workers/         Background job execution
frontend/src/
  features/        Video, understanding, and question-generation UI
  shared/          API client, common components, and types
docs/              Architecture, development, API, and deployment guides
docker/            API, worker, frontend images, and Nginx configuration
~~~

## Validation

~~~bash
python -m pytest backend/tests
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
~~~

See [docs/TESTING.md](docs/TESTING.md) for test scope and setup. See [docs/API.md](docs/API.md) for the HTTP API reference.
