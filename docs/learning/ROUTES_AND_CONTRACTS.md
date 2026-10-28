# Routes and function contracts

Read this with [the main guide](README.md). Paths below have base prefix `/api/v1`. Inputs describe HTTP data, not constructor-injected Python dependencies. All current application route families and compatibility aliases are included; see [source atlas](SOURCE_ATLAS.md) for exact handler signatures.

`GET` retrieves, `POST` submits/creates/performs an action, `PATCH` changes selected fields, and `DELETE` requests deletion/cancellation. Path parameters identify a resource; query parameters modify a request; headers carry metadata/credentials; a body contains structured data or uploaded bytes.

## Shared conventions

- JSON requests use `Content-Type: application/json`. Browser `FormData` sets its own multipart boundary; do not manually set a bare multipart header.
- Temporary-resource requests commonly carry `X-Session-Token`; selected endpoints also accept `?token=`. `X-Session-ID` is an identifier, not interchangeable with an authorization token.
- Credential enforcement differs by route in the current implementation. In particular, some job checks reject an invalid supplied token but do not require a missing token. Do not infer uniform authorization from the fact that the client always sends headers; inspect the route and dependency helpers.
- Success is normally `200`; uploads/extraction/synchronous generation declare `201`; queue submissions declare `202`. `202` confirms acceptance, not completion.
- Pydantic validation typically produces `422`; missing resources commonly produce `404`; permission errors `403`; incompatible lifecycle state `409`; upload/request limits can produce `400` or middleware `413`; processing errors can produce `500`. These are patterns, not a promise that every route implements every error.
- Standard FastAPI error bodies use `{"detail": ...}`. The frontend client extracts that field for display. A response type can filter out extra internal fields.

## Main workflow with concrete data

### 1. Prepare a local clip

No API request is needed to open/preview a local file. `useLocalVideo.selectFile(file)` returns a boolean and sets browser state. Select source seconds 120–145, then either run a generated FFmpeg command and import its output, import an existing clip, or use experimental browser capture.

The staged clip carries both file bytes and provenance: source filename/reference, source interval, measured duration, extraction method, alignment status, and user confirmation. A staged clip is still a browser object; it has no server `video_id` yet.

### 2. Upload the prepared clip

`POST /videos/upload-clip`

Multipart form input:

| Field | Required? / type | Meaning |
| --- | --- | --- |
| `file` | Required binary upload | The prepared clip, not a path string |
| `session_id`, `session_token` | Optional strings | Continue an existing temporary session; also accepted from headers |
| `source_filename` | Optional string | Descriptive original filename, not a trusted server path |
| `source_video_ref` | Optional string | Client source-instance identifier |
| `source_start_seconds`, `source_end_seconds` | Optional floats | Claimed bounds in original recording |
| `source_duration_seconds` | Optional float | Intended interval duration |
| `extraction_method` | Optional string | Native-assisted/import/capture provenance |
| `alignment_status` | Optional string | Temporal alignment provenance |
| `user_confirmed` | Boolean, default true in route | User's association confirmation |

The client method maps camelCase TS metadata to snake_case form fields. The backend reads bytes, enforces upload size/quota, probes media, validates duration, and saves media plus metadata/session bookkeeping.

Response: `201 VideoDetailResponse`. Important fields are `video_id`, `filename`, `duration_seconds`, `size_bytes`, `created_at`, `width`, `height`, `fps`, `codec_name`, `is_temporary`, session credentials/expiry, and source/alignment metadata. Credentials are also returned in response headers. Values below are illustrative; server IDs are generated:

```json
{
  "video_id": "clip_example",
  "filename": "clip_example.mp4",
  "duration_seconds": 25.0,
  "size_bytes": 344064,
  "created_at": "2026-10-28T00:00:00+00:00",
  "is_temporary": true,
  "session_id": "example-session",
  "session_token": "example-token",
  "source_start_seconds": 120.0,
  "source_end_seconds": 145.0
}
```

The default byte limit is `1024 * 1024 * 1024` (1 GiB, labeled “1 GB” in the UI), and duration limit 600 seconds. The measured duration is more authoritative than a filename or browser claim.

### 3. Submit analysis

`POST /jobs/video-understandings`, JSON:

```json
{"video_id": "clip_example", "fps": 2.0, "max_new_tokens": 1024}
```

`video_id` is required, 1–200 characters, constrained to the identifier regex in `job_schema.py`. `fps` defaults to 2, must be finite and `0 < fps <= 30`. `max_new_tokens` defaults to 1024, allowed 64–4096.

Response: `202 {"job_id":"job_<32 hex characters>","status":"queued"}`. The handler validates availability/lifecycle, creates an `InferenceJob`, stores it, and returns. It does not load Qwen.

The live worker currently uses its environment-configured sampling/output settings rather than reading this job's `fps`/`max_new_tokens` in `handle_job`. Accepting and storing a field is different from consuming it.

### 4. Poll

`GET /jobs/{job_id}` returns `JobStatusResponse`:

```text
job_id, job_type, status,
analysis_id?, video_id?,
created_at, started_at?, finished_at?,
result_id?, error_message?
```

`?` here means optional/nullable, not query-string syntax. Timestamps are serialized timezone-aware datetimes. The UI client waits 2000 ms between polls by default, until `completed` or `failed`. There is currently no maximum elapsed timeout or AbortSignal in that polling helper. A network exception rejects the promise; a server-reported failed job is returned and then interpreted by the caller.

### 5. Load the result

`GET /analyses/{result_id}` returns `AnalysisDetailRepsonse` (the class name contains that spelling in source):

```text
analysis_id, clip_name, model_name,
scene?, participants?, objects[], summary, events[],
source_video_name?, source_start_seconds?, source_end_seconds?,
temporal_alignment_status?, is_temporary?, is_persistent?, video_available,
is_mock, inference_mode, sampling_fps?, runtime_seconds?, device?, mock_notice?,
window_analysis_ids?
```

Each event includes start/end, description, actor/action/object_name/target/confidence, optional clip/source timestamp representations, uncertainty, and evidence provenance. In single-clip analysis, domain event start/end are clip-relative; the API can add source mapping. Merged-window records use a special source-coordinate path in the router.

### 6. Generate questions

`POST /jobs/question-generations`:

```json
{
  "analysis_id": "the_returned_analysis_id",
  "clip_duration_seconds": 25.0,
  "max_questions": 5,
  "criteria_text": "Focus on observable object interactions."
}
```

Required: analysis ID and finite positive clip duration. Maximum questions defaults to 5, allowed 1–20. Criteria text defaults empty, maximum 16,384 characters. The analysis must already exist.

Response: the same queued submission shape. Poll, then `GET /question-generations/{result_id}`:

```text
generation_id, analysis_id, generator, question_count,
is_persistent, questions[]
```

Each question has `question`, nullable `answer`, `actor_reference`, `source_event_index`, `evidence {clip_name,start_seconds,end_seconds}`, `generation_method`, and `review_status`. Draft Qwen candidates use `answer=None`; do not assume generation also identifies the actor answer. A requested maximum is an upper bound; filtering can yield fewer candidates or none.

## Complete route catalogue

### Health and maintenance

| Method and path | Input | Output and side effect |
| --- | --- | --- |
| GET `/health` | None | `HealthResponse`: `status="ok"`, service name; liveness/identity, not a full GPU/model readiness test |
| POST `/cleanup/temporary-storage` | Admin token header/bearer authorization | Alias delegating temporary cleanup; returns purged identifiers/count |

### Videos

Source: `api/routers/videos.py`; schemas: `video_schema.py`.

| Method and path | Input | Output / side effect |
| --- | --- | --- |
| GET `/videos` | Optional session ID query/header; token header/query | `VideoListResponse {videos:[VideoSummaryResponse],total}`; global list excludes temporary clips unless a session is requested |
| POST `/videos/upload` | Multipart `file` | `201 VideoDetailResponse`; saves permanent uploaded media; distinct from local preview and temporary clip path |
| POST `/videos/upload-clip` | Multipart fields described above | `201 VideoDetailResponse`; creates temporary media/session resources |
| POST `/videos/temporary-clip` | Same as upload-clip | Hidden OpenAPI compatibility alias |
| DELETE `/videos/temporary-clips/{video_id}` | Temporary ID and `X-Session-Token` | `{video_id,media_deleted,deletion_pending}`; deletion can defer while media is protected |
| POST `/videos/session/{session_id}/touch` | ID, token header/query | `{session_id,expires_at,last_active_at,state,status}`; renews meaningful-activity timestamp |
| POST `/videos/cleanup-temporary` | `X-Internal-Token` or authorization; no required JSON body | `{purged_video_ids,purged_clip_ids,purged_count,status}`; deletes expired eligible temporary resources |
| GET `/videos/{video_id}` | ID and applicable credentials | `VideoDetailResponse`; missing or unauthorized temporary media produces an error; may record activity |
| GET `/videos/{video_id}/stream` | ID, token header/query for temporary media | File bytes with media content type, range handling from `FileResponse`, and `X-Stream-Lease-Id`; acquires/releases a lease |
| POST `/videos/stream-lease/{video_id}/{lease_id}/renew` | IDs; token header or query (`token`, legacy `session_id` alias) | `{status:"renewed",video_id,lease_id}`; extends existing lease; can return 404 for expired lease |
| POST `/videos/{video_id}/clip` | JSON `{timestamp,before_seconds?,after_seconds?}` | `201 ClipExtractionResponse`; creates server-side FFmpeg output file |

Important implementation/deployment distinction: the permanent upload route exists, but Compose mounts `data/videos` read-only. Its existence does not guarantee that this operation can write in the default container configuration. The primary local-first UI uses temporary clip upload.

For server extraction `timestamp` is an HH:MM:SS string, before/after default to **15 seconds at the HTTP schema**, each 0–120. The lower-level `ClipRequest` dataclass defaults to **30 seconds**, so explicitly passing values avoids mixing defaults across layers.

### Jobs

Source: `api/routers/jobs.py`; schemas: `job_schema.py`.

| Method and path | Input | Output / side effect |
| --- | --- | --- |
| POST `/jobs/video-understandings` | `VideoUnderstandingJobRequest` | `202 JobSubmissionResponse`; inserts video job |
| POST `/jobs/video-understanding` | Same | Hidden singular compatibility alias |
| POST `/jobs/question-generations` | `QuestionGenerationJobRequest` | `202 JobSubmissionResponse`; inserts question job |
| POST `/jobs/question-generation` | Same | Hidden singular compatibility alias |
| GET `/jobs/{job_id}` | Valid `job_` + 32 hex ID, applicable token | `JobStatusResponse`; reads job |
| DELETE `/jobs/{job_id}` | Valid ID, temporary-job token as applicable | `JobStatusResponse`; immediate queued failure or running cancel request, not physical row deletion |

### Analyses

Source: `api/routers/analyses.py`; schemas: `analysis_schema.py`, plus `MergeWindowsRequest` defined in the router.

| Method and path | Input | Output / side effect |
| --- | --- | --- |
| GET `/analyses` | No required body | `{analyses:[{analysis_id,clip_name,model_name,event_count}]}`; default repository listing excludes `clip_` temporary IDs |
| GET `/analyses/{analysis_id}` | ID, optional credentials for temporary access paths | Full structured analysis and provenance; may load sidecar/session metadata |
| POST `/analyses/{analysis_id}/save-persistent` | ID, applicable token | Full analysis response with persistence state; changes cleanup retention for structured results |
| POST `/analyses/merge-windows` | JSON described below; session token header | `{analysis_id,event_count,window_count,window_analysis_ids}`; writes a merged analysis and session association |

Merge input: `analysis_ids` (2–12 unique temporary `clip_` IDs), `source_filename` (1–500 chars), finite nonnegative `source_start_seconds`, finite positive `source_end_seconds`, and end after start. Windows must have persisted source timing, belong to one authorized session, match the source recording, and fall within the selected interval. Events are converted into source time, sorted, and matching strongly overlapping duplicates are combined by retaining provenance. The response is a summary, not the full merged record; fetch its analysis ID afterward.

### Questions

Source: `api/routers/questions.py`; schemas: `question_schema.py`.

| Method and path | Input | Output / side effect |
| --- | --- | --- |
| POST `/question-generations` | `{analysis_id,generator?:"template",clip_duration_seconds,max_questions?:5,criteria_text?:""}` | `201 QuestionGenerationResponse`; synchronous template path, saves a generation record |
| GET `/question-generations/{generation_id}` | `gen_` + 32 hex ID, applicable token | `QuestionGenerationResponse`; reads saved record, does not regenerate |
| POST `/question-generations/{generation_id}/save-persistent` | ID and applicable token | Generation response with persistence state; changes retention |

The synchronous route accepts only `generator="template"`. The async job route uses whichever generator the worker was configured with. These are two different execution paths.

### Retained grounded question answering

Source: `api/routers/qa.py`; schemas: `qa_schema.py`.

| Method and path | Input | Output / side effect |
| --- | --- | --- |
| POST `/qa/videos/{video_id}/ask` | JSON `{question,analysis_id?}`; token as applicable | `VideoQAResponse`; answers against video/analysis evidence |
| POST `/qa/analyses/{analysis_id}/ask` | JSON `{question}`; token as applicable | Same response grounded in that saved analysis |

Question strings are 2–500 characters. Output fields: `question`, `answer`, `confidence`, `confidence_type`, `is_human_reviewed`, `is_observable`, `uncertainty_notes`, start/end, `evidence_reasoning`, `referenced_events`, optional video/analysis/clip URL, mock provenance. **The field is `is_observable`, not `observable`; there is no `evidence_timestamps` list in the current response schema.** Older prose/examples can differ.

The default `get_qa_service()` builds `GroundedVideoQAService` without an `llm_generator` callback. Its analysis-based path uses event matching. The service also has an optional model-based path when explicitly supplied that text-generation callback, with rule-based fallback on errors; inspect construction before assuming it calls Qwen. These retained APIs are separate from the current two-tab main workspace.

### Retained review and export

Source: `api/routers/annotations.py`; schemas: `annotation_schema.py`.

| Method and path | Input | Output / side effect |
| --- | --- | --- |
| POST `/annotations/sessions` | `{analysis_id,video_id?,generation_id?,reviewer_id?}` | `201 ReviewSessionResponse`; creates or loads a review session with original snapshots |
| GET `/annotations/sessions` | Optional session token header/query | Array of `ReviewSessionSummary`; temporary sessions filtered by credentials |
| GET `/annotations/sessions/{review_id}` | Review ID and applicable token | Full `ReviewSessionResponse` |
| PATCH `/annotations/sessions/{review_id}/events/{event_index}` | Event update described below | Full updated session; stores event review/edit |
| PATCH `/annotations/sessions/{review_id}/questions/{question_index}` | Question update described below | Full updated session; stores question review/edit |
| PATCH `/annotations/sessions/{review_id}/status` | `{overall_status,summary?}` | Full updated session |
| POST `/annotations/sessions/{review_id}/sync-questions` | `{generation_id}` | Full updated session; merges generated questions into review session |
| POST `/annotations/sessions/{review_id}/save-persistent` | Review ID, applicable credentials | Full updated session; changes persistence |
| POST `/annotations/reviews/{review_id}/save-persistent` | Same | Hidden compatibility alias |
| POST `/annotations/sessions/{review_id}/persist` | Same | Hidden compatibility alias |
| POST `/annotations/reviews/{review_id}/persist` | Same | Hidden compatibility alias |
| GET `/annotations/sessions/{review_id}/export/whodunnit` | ID and applicable token header/query | JSON export payload produced by adapter, not a review session response |
| GET `/annotations/sessions/{review_id}/export/csv` | Same | CSV text download; check response headers and adapter columns |

Event update requires `status` (`pending`, `accepted`, `rejected`, `edited`) and optionally `reviewer_notes`, edited start/end, description, actor, action, object, target. Question update requires the same review status and optionally notes, edited question, edited answer. Session status uses `in_progress`, `approved`, `rejected`.

`ReviewSessionResponse` contains IDs, created/updated timestamps, reviewer, overall status/summary, persistence/video availability/mock provenance, event review items, and question review items. Each review item preserves original values alongside edited values. This is useful provenance: “what did the model say?” and “what did the reviewer change?” remain different questions.

FastAPI also supplies `/openapi.json`, `/docs`, `/redoc`, and their supporting docs endpoints outside `/api/v1`. Hidden aliases are registered routes even when omitted from generated OpenAPI documentation.

## Function contracts: where the HTTP request becomes Python work

### Three forms of clip extraction

Do not confuse these similarly named operations:

| Operation | Inputs | Return | Side effects |
| --- | --- | --- | --- |
| `generateNativeCommand(shell, options)` | Shell `powershell/cmd/bash`; source filename/path placeholder, numeric start/end, mode `frame_accurate/fast_copy`, optional output name | `GeneratedNativeCommand` with command/script text, extension, output filename, mode/warning metadata | Pure command construction; does not execute FFmpeg |
| `extractClipWithBrowserCapture(sourceFile,startSeconds,endSeconds,onProgress?,signal?)` | Browser `File`, interval, optional callback/AbortSignal | `Promise<BrowserCaptureResult>` | Plays/captures locally, allocates/revokes URLs/tracks; produces a new file |
| `VideoClipExtractor.extract(request)` | Python `ClipRequest` referencing an existing server-accessible file | `ClipResult` | Probes duration, creates output file by running FFmpeg |

Browser capture returns a `File`, object URL, filename/bytes, measured/requested duration and delta, wall-clock capture duration, playback rate, MIME type, background-throttling flag, and optional warning. It can reject unsupported capture, cancellation, decoding/recording problems. It is not an instantaneous byte slice of a compressed MP4.

### Server clip extraction, fully worked

```python
from pathlib import Path
from castle_qa.domain.clip_request import ClipRequest
from castle_qa.services.video_clip_extractor import VideoClipExtractor
from castle_qa.services.video_probe import VideoProbe
from castle_qa.utils.timestamp import Timestamp

request = ClipRequest(
    video_path=Path("data/videos/your_existing_video.mp4"),
    timestamp=Timestamp("00:01:30"),
    before_seconds=15.0,
    after_seconds=15.0,
)
extractor = VideoClipExtractor(
    video_probe=VideoProbe(),
    output_dir=Path("data/clips"),
)
result = extractor.extract(request)
```

The filename is a placeholder; substitute a real file. Both constructor collaborators must be supplied in the present implementation even though their annotations/defaults allow `None`: the constructor immediately calls `output_dir.mkdir` and extraction needs the probe.

For a source longer than 105 seconds, center 90, before/after 15 gives start 75, end 105, duration 30. Near the beginning/end:

```text
start = max(0, center - before)
end = min(video_duration, center + after)
duration = end - start
```

`ClipResult` contains source/output `Path` objects, selected timestamp string, start/end strings, actual before/after lengths, and duration. `to_dict()` converts paths to strings for JSON serialization. The HTTP response excludes actual before/after lengths and returns paths as strings; it does not return video bytes. Use streaming/file handling for media.

Errors include missing source (dataclass raises `FileNotFoundError`), negative before/after (`ValueError`), timestamp beyond duration (`ValueError`), and FFmpeg subprocess failure. This extractor invokes FFmpeg with H.264/AAC re-encoding and `-y`, so its server-side naming can overwrite an existing same-named output. Generated user-facing native commands intentionally omit `-y`. Those paths have different overwrite behavior.

### Main backend contracts

| Function | Inputs | Return and errors | Side effects |
| --- | --- | --- | --- |
| `VideoProbe.get_metadata(path)` | Video file `Path` | Media metadata incl. duration; errors if probing fails | Runs ffprobe |
| `VideoService.save_temporary_clip(...)` | Binary stream, original filename, MIME, optional session credentials/source metadata | `VideoItem`; validation/permission failures | Writes media/metadata/session resources and quota reservations |
| `InferenceJob.new_video_understanding(...)` | Media ID/path, sampling/token parameters, metadata/session | Queued domain `InferenceJob` | In-memory construction, generated ID/time; persistence is separate |
| `InferenceJob.new_question_generation(...)` | Analysis ID, duration, maximum, criteria text | Queued domain job | Same construction distinction |
| `JobRepository.create(job)` | Queued domain job | `None`; rejects invalid ID/state | Commits SQL insert |
| `JobRepository.get(job_id)` | Valid job ID | Domain job or `None` | SQL read |
| `JobRepository.claim_next(worker_id?)` | Optional worker identity | Running domain job or `None` | Atomic SQL claim, attempt increment, token/timestamps |
| `JobRepository.heartbeat(job_id,claim_token)` | Owned running job | Boolean indicating update succeeded | SQL liveness timestamp |
| `InferenceJobWorker.process_next()` | No per-call arguments; collaborators injected in constructor | Terminal job or `None` for empty queue; can raise if ownership/state recording fails | Claims, starts heartbeat thread, calls handler, records completion/failure, terminal cleanup |
| Injected `handle_job(job)` | Claimed job and payload | Result ID string | Dispatches video or question workflow |
| `VideoUnderstandingWorkflow.analyze_video(video_path,...)` | Existing `Path`; optional clip bounds/duration/source metadata | `VideoUnderstandingResult {analysis_id,analysis,output_path}` | Probe if needed, infer, save JSON |
| `VideoUnderstandingService.analyze(clip)` | `ClipResult` | Domain `VideoAnalysis`; abstract contract implemented by mock/Qwen | Implementation-specific inference |
| `LocalQwenVideoUnderstandingService.generate_text(prompt,max_new_tokens=768)` | Text and positive token limit | Generated text string | Uses loaded GPU model |
| `QuestionWorkflow.generate(analysis_id,criteria,clip_duration_seconds,create_generation_record=False)` | Existing analysis ID, `QACriteria`, positive duration, optional record flag | `QuestionGenerationResult` or `None` when analysis missing | Loads, generates, validates, saves; optional `gen_...` ID |
| `QwenLocalQuestionGenerator.generate(analysis,criteria)` | Domain analysis and criteria | `list[QuestionCandidate]`, possibly empty; invalid model JSON can raise | Model generation and conditional raw-output artifact |
| `QuestionValidator.validate(candidates,criteria,clip_duration_seconds=None)` | Candidates, constraints, optional bound | Accepted subset; at most configured maximum | Filtering, no persistence/model call |
| `VideoAnalysisRepository.save(analysis)` | Domain object | Output `Path` | Writes `<clip_stem>_analysis.json` |
| `VideoAnalysisRepository.load(analysis_id)` | Valid identifier | Domain analysis or `None`; invalid identifier raises | Reads JSON and reconstructs objects |
| `QuestionRepository.save(...)` | Analysis, criteria, accepted candidates and record metadata | Output `Path` | Writes generation JSON |
| `VideoService.delete_temporary_clip(video_id,job_repository?)` | Temporary ID, optional queue collaborator | Boolean; false can mean deletion deferred | Coordinates job/stream protection, deletion/pending metadata |

Exact defaults and helper functions are indexed in [SOURCE_ATLAS.md](SOURCE_ATLAS.md). Read constructors too: a method's apparent short signature often relies on injected repositories/settings established earlier.

## UI function contracts

| Function | Input → output | What changes |
| --- | --- | --- |
| `useLocalVideo(onVideoSelected?)` | Optional callback → state, errors, file selection/clear/dialog functions and input ref | Hook manages local File/Object URL ownership |
| `selectFile(file)` | File → boolean | Sets local video or error; revokes previous URL |
| `handleOpenExtraction(interval)` | `{start,end,label?}` → void | Opens modal if within source interval limit |
| `handleClipStaged(clip)` | `StagedClipItem` → void | Replaces staged clip and invalidates old analysis/UI work |
| `handleAnalyzeStagedClip(clip)` | Staged clip → `Promise<void>` | Upload, submit, poll, load; updates progress/error/analysis |
| `handleGenerateQuestions(criteriaText)` | String → Promise of generation on success | Requires analysis; manages busy state; rejects failures for child UI |
| `api.uploadTemporaryClip(file,metadata?,onProgress?)` | Browser File and provenance → Promise of video/session metadata | HTTP upload; saves credentials in module memory |
| `api.pollJobUntilFinished(jobId,intervalMs=2000,onUpdate?)` | ID/settings → Promise of terminal job | Repeated HTTP requests; no built-in timeout/cancel |
| `createAnalysisWindows(start,end,windowSeconds=90,overlapSeconds=10)` | Finite valid interval, <=600s → windows | Pure calculation; retained helper, not main App's one-clip path |

Notice which functions catch exceptions and which propagate them. `handleAnalyzeStagedClip` normally stores an error in React state; `handleGenerateQuestions` propagates an error so its child workspace can handle it. An “async function” always returns a Promise in JavaScript, even when its useful result is only UI state updates.
