
# CASTLE QA Studio — Deployment Guide

## 1. Overview

CASTLE QA Studio is a modular application for generating
video-grounded question suggestions from structured video
analysis results.

The current Docker deployment includes:

- FastAPI REST backend
- Template Question Generator
- Video Analysis API
- Saved Question Generation API
- Persistent JSON storage

**Current deployment stage:** 3A.5 — CPU-only FastAPI.

The React frontend and Qwen GPU worker will be added later.

This deployment is intended for local development and
private testing. It is not yet a public production service.

## 2. Requirements

Before starting, install:

- Docker Engine or Docker Desktop
- Docker Compose v2
- Git
- Python 3.10+ (to run the host-side smoke test)

For Windows development, use Docker Desktop with
Linux containers enabled.

Verify Docker:

```bash
docker --version
docker compose version
docker info
```

## 3. Get the Project

Clone the repository if it is not already available:

```bash
git clone https://github.com/tito-tom/castle_question_generation.git
cd castle_question_generation
```

Use a branch or release containing the FastAPI Docker setup.

## 4. Prepare Persistent Storage

The API uses two directories:

```text
data/
├── analysis/
│   └── *_analysis.json
└── questions/
    └── api_template/
```

Create them if necessary.

On Linux:

```bash
mkdir -p data/analysis data/questions/api_template
```

Place permitted analysis JSON files in `data/analysis`.

The directories are mounted into the container through
Docker Compose.

The analysis directory is read-only inside the container.
The question directory must be writable by the container
user (UID 10001).

On Linux, configure host-directory ownership or permissions
appropriately before running the container.

Do not commit CASTLE videos or private analysis data to Git.

## 5. Build and Start the Backend

From the repository root:

```bash
docker compose config
docker compose up -d --build
```

Verify that the container started:

```bash
docker compose ps
```

Check logs:

```bash
docker compose logs -f api
```

Press Ctrl+C to stop following the logs.

## 6. Access the API

The current Compose configuration binds port 8000
to the host loopback interface.

Health endpoint:

http://127.0.0.1:8000/api/v1/health

Swagger UI:

http://127.0.0.1:8000/docs

Available endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/v1/health | API health |
| GET | /api/v1/analyses | List analyses |
| GET | /api/v1/analyses/{analysis_id} | Analysis detail |
| POST | /api/v1/question-generations | Generate questions |
| GET | /api/v1/question-generations/{generation_id} | Retrieve saved results |

The API is accessible locally on the Docker host.
Remote access is not configured.

## 7. Verify the Deployment

Run the read-only smoke test from the host:

```bash
python3 scripts/smoke_test_api.py
```

This checks:

1. API health
2. Analysis listing
3. Analysis detail retrieval

At least one valid analysis JSON file must be available.

To test generation and persistence:

```bash
python3 scripts/smoke_test_api.py \
  --analysis-id kitchen_8_day_1_at_00-40-00 \
  --clip-duration 60
```

Replace the analysis ID and duration with values
appropriate for your available test data.

The second command creates a new generation record.

## 8. Verify Persistent Storage

Generated question JSON files should appear in:

```text
data/questions/api_template/
```

Stop and recreate the containers:

```bash
docker compose down
docker compose up -d --build
```

Previously saved generation records should remain available
because they are stored in host-mounted directories.

Container recreation does not replace backups.

## 9. Update the Application

After changes have been committed and pushed:

```bash
git pull --ff-only
docker compose up -d --build
docker compose ps
python3 scripts/smoke_test_api.py
```

Use the appropriate tested branch or release.

For future production use, deployment should use pinned
release versions rather than automatically following
unreviewed changes.

## 10. Stop the Application

Stop containers:

```bash
docker compose stop
```

Stop and remove the Compose containers and networks:

```bash
docker compose down
```

Host bind-mounted analysis and question files are retained.

## 11. Troubleshooting

### Port 8000 is already in use

Stop the locally running Uvicorn server or another container
using port 8000.

### No analyses appear

Check that:

- `data/analysis/` contains analysis JSON files.
- Filenames end with `_analysis.json`.
- The JSON files are valid.
- The Docker bind mount is correctly configured.

### Permission denied when saving questions

The API runs as UID 10001 inside its container.

Ensure the host-mounted question directory is writable
by that user. On Linux, adjust directory ownership or
permissions according to your server's access policy.

### Container fails to start

Inspect:

```bash
docker compose ps
docker compose logs --tail=100 api
```

### Changes do not appear in the container

Rebuild:

```bash
docker compose up -d --build
```

## 12. Security and Production Limitations

The current deployment:

- Has no user authentication.
- Has no HTTPS reverse proxy.
- Does not expose the service publicly.
- Does not yet have database-backed jobs.
- Does not include Qwen GPU inference.
- Does not include automated backups.

Do not expose this API directly to the public internet.

Before public deployment, add authentication, HTTPS,
request limits, storage validation, monitoring, backups,
and dataset access controls.

## 13. Future Deployment Components

The planned full application will add:

- React + TypeScript frontend
- GPU inference worker
- Qwen2.5-VL-7B-Instruct
- Persistent job tracking
- Human annotation and review storage
- HTTPS reverse proxy
- Environment-specific deployment configuration

The deployment goal is to start the complete application
with Docker Compose on an appropriately configured server.
