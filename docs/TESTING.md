# CASTLE QA Studio — Testing Strategy & Test Suites

This document provides a comprehensive guide to testing CASTLE QA Studio, including backend unit/integration tests, frontend component tests, and Playwright browser end-to-end (E2E) tests.

---

## 1. Overview of Test Suites

| Suite | Runner / Framework | Test Count | Target Area |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Integration** | `pytest` + `pytest-asyncio` + `TestClient` | **181 tests** | REST API, database repositories, worker queue, storage lifecycles, stream leases, upload quotas, security, inference provenance |
| **Frontend Unit & Component** | `node:test` + `vitest` + React Testing Library | **74 tests** | Local video isolation, interval selection, extraction modals, timeline views, QA panels, review workflows |
| **Browser End-to-End (E2E)** | Playwright (Microsoft Edge headless) | **15 tests** | Real browser workflows, local video playback, short-clip upload, mock worker jobs, copy/download, persistent saving |
| **Frontend Production Build** | TypeScript (`tsc`) + Vite | **0 errors** | Static typing, production bundling, asset optimization |

---

## 2. Backend Test Suite (Pytest)

### 2.1 Execution Command
```powershell
& 'C:\Users\TITO TOM\miniconda3\envs\yolo_seg_root\python.exe' -m pytest backend/tests -v
```

### 2.2 Key Test Modules
- [test_api_videos.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_api_videos.py): Video ingestion, temporary uploads, stream range requests, and error cases.
- [test_api_jobs.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_api_jobs.py): Asynchronous GPU job submission, queue status polling, claim tokens, and validation.
- [test_temporary_safety_and_lifecycle.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_temporary_safety_and_lifecycle.py): 24-hour meaningful inactivity TTL, session touch, and cleanup safeguards.
- [test_temporary_clips.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_temporary_clips.py): Size and duration limits during chunked streaming uploads.
- [test_task7b_verification.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_task7b_verification.py): Cross-process stream lease tracking and lease touch API.
- [test_task7c_verification.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_task7c_verification.py): Canonical inference mode hardening (`real` vs `mock`), production cleanup secret validation, and session authorization for stream renewal.
- [test_task7d_verification.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_task7d_verification.py): Deterministic stream lease renewal beyond 5-minute threshold, protection of actively streaming uploads vs eviction of crashed upload reservations, route aliases, and mode-aware readiness checker.
- [test_task7d1_provenance.py](file:///d:/DCU-Internship/castle-question-generation/backend/tests/test_task7d1_provenance.py): Historical inference provenance, strict classification of real vs mock vs legacy_unverified, resolution of contradictory metadata, and Whodunnit export provenance tagging.

### 2.3 Test Design Standards
- **Strict Isolation**: All tests run with isolated temporary directories (`tmp_path`) and isolated SQLite in-memory or temporary databases.
- **Injectable Time**: Time-sensitive tests (e.g., inactivity expiration and stream lease TTL) use injectable timestamps or `unittest.mock.patch("time.time")`.
- **Zero Network Egress**: Tests never upload large media or contact external endpoints.

---

## 3. Frontend Test Suite (Node + Vitest)

### 3.1 Execution Command
```powershell
npm --prefix frontend test
```

### 3.2 Key Test Files
- `tests/test_local_video.mjs` (10 tests): Pure Node test suite verifying that selecting a local video file generates isolated `blob:` Object URLs and **NEVER** calls the upload API.
- `tests/clip_selection.test.tsx` (15 tests): Interval selection, boundary validation, scrubbing, and timeline segment selection.
- `tests/clip_extraction.test.tsx` (16 tests): Modal extraction workflows (Mode A native FFmpeg commands without forced overwrite `-y`, Mode B file drop, Mode C browser capture).
- `tests/clip_upload_and_understanding.test.tsx` (9 tests): Explicit short-clip upload transmits only the extracted clip (not the 1.28 GB source) and transitions into timeline analysis.
- `tests/task5_understanding_qa_review.test.tsx` (17 tests): Grounded QA query submission, heuristic confidence badges, event editing, and Whodunnit export generation.
- `tests/qa_and_video_switching.test.tsx` (7 tests): Source video switching, local state clearance, and Object URL revocation.

---

## 4. Playwright Browser End-to-End Suite

### 4.1 Prerequisites
Before running Playwright, launch the three background services:
1. FastAPI Backend on `http://127.0.0.1:8000`.
2. Mock Worker (`python -m castle_qa.workers.entrypoint --mock`).
3. Frontend Dev Server on `http://localhost:3000`.

### 4.2 Execution Command
```powershell
npm --prefix frontend run test:e2e
```

### 4.3 Test Journey Inventory (15 Tests)
- **Test A**: Clean initial workspace render, empty states, zero network traffic.
- **Test B**: Local CASTLE video selection (`kitchen_8_day_1.mp4`), HTML5 video playback, timeline scrubbing, zero network upload.
- **Test C**: Timestamp interval selection (`120.0s` to `145.0s`, duration `25.0s`), boundary validation.
- **Test D**: Extraction modal verification: Mode A command format, Mode C capabilities, Mode B drag-and-drop staged clip card.
- **Test E**: Explicit short-clip upload transmits **ONLY** the ~336 KB staged clip and receives temporary session credentials.
- **Test F**: Qwen mock video understanding analysis completes with amber `[MOCK INFERENCE]` badge and chronological event timeline.
- **Test G**: Grounded Video QA with observable facts, heuristic confidence badge, and unanswerable query ("What is the weather outside?").
- **Test H**: Question generation job submission, worker polling, and review alert.
- **Test I**: Whodunnit review workspace: accepting events, editing actor names, rejecting questions, synchronizing questions.
- **Test J**: Copy and download functionality: Whodunnit JSON package, CSV spreadsheet.
- **Test K**: Explicit "Save to Library" persistent saving.
- **Test L**: Source video switching, state teardown, and Object URL cleanup.
- **Interval Preview & Capture (2 tests)**: Playback bounded strictly within selected interval; experimental browser capture with cancellation.
- **Smoke test**: Microsoft Edge launch verification.

---

## 5. Mock vs Real Inference Semantics

To ensure scientific integrity and prevent misleading benchmark results:

| Feature | Mock Inference Mode (`mock`) | Real Inference Mode (`real`) |
| :--- | :--- | :--- |
| **Worker Execution** | [MockVideoUnderstandingService](file:///d:/DCU-Internship/castle-question-generation/backend/src/castle_qa/services/video_understanding/mock_video_understanding_service.py) | [LocalQwenVideoUnderstandingService](file:///d:/DCU-Internship/castle-question-generation/backend/src/castle_qa/services/video_understanding/local_qwen_video_understanding_service.py) |
| **Question Generator** | [TemplateQuestionGenerator](file:///d:/DCU-Internship/castle-question-generation/backend/src/castle_qa/services/question_generation/template_question_generator.py) | [QwenLocalQuestionGenerator](file:///d:/DCU-Internship/castle-question-generation/backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py) |
| **Hardware Requirement** | CPU only (Laptop / CI) | NVIDIA GPU with >= 16 GB VRAM |
| **Duration** | 2–4 seconds per job | 30–90 seconds per job (depending on FPS & VRAM) |
| **UI Banner** | Amber badge: `[MOCK INFERENCE]` | Green badge: `[REAL INFERENCE]` |
| **Export Provenance** | `model_name: "mock-qwen-video"`, `is_mock: true` | `model_name: "Qwen/Qwen2.5-VL-7B-Instruct"`, `is_mock: false` |

