# CASTLE QA Studio — Authoritative API Reference

This document provides the authoritative REST API reference for CASTLE QA Studio, based on actual FastAPI route registration and the application's OpenAPI specification (`GET /openapi.json`).

Base API URL prefix: `/api/v1`

---

## 1. Summary of Registered Endpoints

| HTTP Method | Path | Router Name | Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | `heal_check` | Canonical | Server health and service identification |
| `POST` | `/api/v1/cleanup/temporary-storage` | `cleanup_temporary_storage_alias` | Route Alias | Trigger temporary storage cleanup with administrative token |
| `GET` | `/api/v1/videos` | `list_videos` | Canonical | List registered videos and metadata |
| `POST` | `/api/v1/videos/upload` | `upload_video` | Canonical | Upload persistent server video (admin/dev) |
| `POST` | `/api/v1/videos/upload-clip` | `upload_temporary_clip` | Canonical | Stream upload and validate extracted short clip |
| `POST` | `/api/v1/videos/temporary-clip` | `upload_temporary_clip` | Route Alias | Alias for `/videos/upload-clip` |
| `GET` | `/api/v1/videos/{video_id}` | `get_video_detail` | Canonical | Retrieve detailed metadata for a video or clip |
| `GET` | `/api/v1/videos/{video_id}/stream` | `stream_video` | Canonical | Stream video with byte-range and lease tracking |
| `POST` | `/api/v1/videos/{video_id}/clip` | `extract_video_clip` | Canonical | Server-side FFmpeg clip extraction |
| `POST` | `/api/v1/videos/session/{session_id}/touch` | `touch_session` | Canonical | Touch temporary session to extend 24h inactivity TTL |
| `POST` | `/api/v1/videos/stream-lease/{video_id}/{lease_id}/renew` | `renew_stream_lease` | Canonical | Extend active stream lease beyond 5-minute TTL |
| `POST` | `/api/v1/videos/cleanup-temporary` | `cleanup_temporary_media` | Canonical | Purge expired temporary media (protected) |
| `POST` | `/api/v1/jobs/video-understandings` | `submit_video_understanding_job` | Canonical | Enqueue Qwen video understanding analysis job |
| `POST` | `/api/v1/jobs/video-understanding` | `submit_video_understanding_job` | Route Alias | Singular alias for `/jobs/video-understandings` |
| `POST` | `/api/v1/jobs/question-generations` | `submit_question_generation_job` | Canonical | Enqueue grounded question generation job |
| `POST` | `/api/v1/jobs/question-generation` | `submit_question_generation_job` | Route Alias | Singular alias for `/jobs/question-generations` |
| `GET` | `/api/v1/jobs/{job_id}` | `get_job_status` | Canonical | Poll background job status and progress |
| `GET` | `/api/v1/analyses` | `list_analyses` | Canonical | List video analyses in storage |
| `GET` | `/api/v1/analyses/{analysis_id}` | `get_analysis` | Canonical | Retrieve structured analysis events and summary |
| `POST` | `/api/v1/analyses/{analysis_id}/save-persistent` | `save_analysis_persistent` | Canonical | Mark temporary analysis persistent |
| `POST` | `/api/v1/qa/videos/{video_id}/ask` | `ask_video_question` | Canonical | Grounded QA query against video |
| `POST` | `/api/v1/qa/analyses/{analysis_id}/ask` | `ask_analysis_question` | Canonical | Grounded QA query against analysis events |
| `POST` | `/api/v1/question-generations` | `generate_question` | Canonical | Synchronous template question generation |
| `GET` | `/api/v1/question-generations/{generation_id}` | `get_saved_generation` | Canonical | Retrieve saved question generation |
| `POST` | `/api/v1/question-generations/{generation_id}/save-persistent` | `save_question_generation_persistent` | Canonical | Mark question generation persistent |
| `GET` | `/api/v1/annotations/sessions` | `list_sessions` | Canonical | List annotation review sessions |
| `POST` | `/api/v1/annotations/sessions` | `create_or_load_session` | Canonical | Initialize or retrieve an annotation review session |
| `GET` | `/api/v1/annotations/sessions/{review_id}` | `get_session` | Canonical | Retrieve current review session state |
| `PATCH` | `/api/v1/annotations/sessions/{review_id}/events/{event_index}` | `update_event_review` | Canonical | Update status or edit fields of an event |
| `PATCH` | `/api/v1/annotations/sessions/{review_id}/questions/{question_index}` | `update_question_review` | Canonical | Update status or edit fields of a question |
| `PATCH` | `/api/v1/annotations/sessions/{review_id}/status` | `update_session_status` | Canonical | Update overall review session status |
| `POST` | `/api/v1/annotations/sessions/{review_id}/sync-questions` | `sync_questions` | Canonical | Synchronize accepted event edits to questions |
| `POST` | `/api/v1/annotations/sessions/{review_id}/save-persistent` | `save_review_session_persistent` | Canonical | Persist review session across cleanups |
| `POST` | `/api/v1/annotations/reviews/{review_id}/save-persistent` | `save_review_session_persistent` | Route Alias | Route alias for `/annotations/sessions/{review_id}/save-persistent` |
| `POST` | `/api/v1/annotations/sessions/{review_id}/persist` | `save_review_session_persistent` | Route Alias | Route alias for persistent save |
| `POST` | `/api/v1/annotations/reviews/{review_id}/persist` | `save_review_session_persistent` | Route Alias | Route alias for persistent save |
| `GET` | `/api/v1/annotations/sessions/{review_id}/export/whodunnit` | `export_whodunnit_json` | Canonical | Download Whodunnit-compatible JSON package |
| `GET` | `/api/v1/annotations/sessions/{review_id}/export/csv` | `export_whodunnit_csv` | Canonical | Download Whodunnit annotations spreadsheet (CSV) |

---

## 2. Core Endpoint Specifications

### 2.1 Temporary Clip Upload
- **Path**: `POST /api/v1/videos/upload-clip` (Alias: `POST /api/v1/videos/temporary-clip`)
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Binary file stream (max 200 MB, max 120s duration).
  - `session_id` (optional): Client session identifier string.
  - `session_token` (optional): Session authorization token.
  - `source_filename` (optional): Original source video name (for display only).
  - `source_start_seconds` (optional): Claimed start second in source video.
  - `source_end_seconds` (optional): Claimed end second in source video.
  - `source_duration_seconds` (optional): Target interval duration.
  - `extraction_method` (optional): `native_ffmpeg_assisted`, `direct_import`, or `browser_capture`.
- **Response** (`201 Created`):
  ```json
  {
    "video_id": "clip_3f8a12bc90d14",
    "filename": "clip_3f8a12bc90d14_kitchen_8_day_1_120_145.mp4",
    "duration_seconds": 25.0,
    "size_bytes": 344064,
    "is_temporary": true,
    "session_id": "sess_89f0a1c2...",
    "session_token": "sess_tok_9918...",
    "expires_at": "2026-10-23T03:00:00+00:00"
  }
  ```

### 2.2 Video Understanding Job Submission
- **Path**: `POST /api/v1/jobs/video-understandings` (Alias: `POST /api/v1/jobs/video-understanding`)
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "video_id": "clip_3f8a12bc90d14"
  }
  ```
- **Response** (`202 Accepted`):
  ```json
  {
    "job_id": "job_018f3a9b-1234-7890-abcd-ef0123456789",
    "status": "queued"
  }
  ```

### 2.3 Job Status Polling
- **Path**: `GET /api/v1/jobs/{job_id}`
- **Response** (`200 OK`):
  ```json
  {
    "job_id": "job_018f3a9b-1234-7890-abcd-ef0123456789",
    "job_type": "video_understanding",
    "status": "completed",
    "result_id": "analysis_clip_3f8a12bc90d14",
    "error_message": null,
    "created_at": "2026-10-22T03:00:00Z",
    "updated_at": "2026-10-22T03:00:05Z"
  }
  ```

### 2.4 Grounded Video Question Answering
- **Path**: `POST /api/v1/qa/videos/{video_id}/ask` (or `POST /api/v1/qa/analyses/{analysis_id}/ask`)
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "question": "Did the actor open the refrigerator?"
  }
  ```
- **Headers**:
  - `X-Session-Token` (required for temporary clips)
- **Response** (`200 OK`):
  ```json
  {
    "video_id": "clip_3f8a12bc90d14",
    "question": "Did the actor open the refrigerator?",
    "answer": "Yes, Person1 opened the refrigerator door.",
    "observable": true,
    "confidence": 0.85,
    "evidence_timestamps": [
      {
        "start_seconds": 12.0,
        "end_seconds": 15.0,
        "source_start_seconds": 132.0,
        "source_end_seconds": 135.0,
        "description": "Person1 opens refrigerator door"
      }
    ]
  }
  ```
  *(Note: `confidence` is a heuristic evidence-matching score, not a calibrated neural probability).*

### 2.5 Stream Lease Renewal
- **Path**: `POST /api/v1/videos/stream-lease/{video_id}/{lease_id}/renew`
- **Headers / Query**:
  - `X-Session-Token: <token>` (or `?token=<token>` / `?session_id=<token>`)
- **Response** (`200 OK`):
  ```json
  {
    "status": "renewed",
    "video_id": "clip_3f8a12bc90d14",
    "lease_id": "a1b2c3d4e5f6"
  }
  ```

### 2.6 Administrative Temporary Storage Cleanup
- **Path**: `POST /api/v1/videos/cleanup-temporary` (Alias: `POST /api/v1/cleanup/temporary-storage`)
- **Headers**:
  - `X-Internal-Token: <CASTLE_INTERNAL_CLEANUP_TOKEN>`
- **Response** (`200 OK`):
  ```json
  {
    "status": "success",
    "purged_count": 0,
    "purged_clips": []
  }
  ```

