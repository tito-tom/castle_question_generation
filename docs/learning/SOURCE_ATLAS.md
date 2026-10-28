# Source atlas

Generated from the current source by `python scripts/generate_learning_atlas.py`. No application modules, database connections, or GPU libraries are imported. This is a lookup index, not a substitute for the explained [contracts](ROUTES_AND_CONTRACTS.md) and [walkthrough](CODE_WALKTHROUGH.md).

Signatures preserve declared arguments/defaults/annotations. Missing return annotations do not mean a function returns nothing. Docstrings describe intent and can lag behavior. Source line links are a snapshot and move when code changes.

## Registered application route declarations

These include hidden compatibility aliases. FastAPI's own documentation endpoints are framework-generated and are not listed here.

| Method | Full path | Handler | Response model | Declared status | Hidden alias |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/analyses` | [list_analyses](../../backend/src/castle_qa/api/routers/analyses.py#L75) | `AnalysisListResponse` | `200 (default)` |  |
| POST | `/api/v1/analyses/merge-windows` | [merge_window_analyses](../../backend/src/castle_qa/api/routers/analyses.py#L98) | `handler-defined` | `200 (default)` |  |
| GET | `/api/v1/analyses/{analysis_id}` | [get_analysis](../../backend/src/castle_qa/api/routers/analyses.py#L221) | `AnalysisDetailRepsonse` | `200 (default)` |  |
| POST | `/api/v1/analyses/{analysis_id}/save-persistent` | [save_analysis_persistent](../../backend/src/castle_qa/api/routers/analyses.py#L355) | `AnalysisDetailRepsonse` | `200 (default)` |  |
| POST | `/api/v1/annotations/sessions` | [create_or_load_session](../../backend/src/castle_qa/api/routers/annotations.py#L220) | `ReviewSessionResponse` | `status.HTTP_201_CREATED` |  |
| GET | `/api/v1/annotations/sessions` | [list_sessions](../../backend/src/castle_qa/api/routers/annotations.py#L347) | `list[ReviewSessionSummary]` | `200 (default)` |  |
| GET | `/api/v1/annotations/sessions/{review_id}` | [get_session](../../backend/src/castle_qa/api/routers/annotations.py#L400) | `ReviewSessionResponse` | `200 (default)` |  |
| PATCH | `/api/v1/annotations/sessions/{review_id}/events/{event_index}` | [update_event_review](../../backend/src/castle_qa/api/routers/annotations.py#L423) | `ReviewSessionResponse` | `200 (default)` |  |
| PATCH | `/api/v1/annotations/sessions/{review_id}/questions/{question_index}` | [update_question_review](../../backend/src/castle_qa/api/routers/annotations.py#L482) | `ReviewSessionResponse` | `200 (default)` |  |
| PATCH | `/api/v1/annotations/sessions/{review_id}/status` | [update_session_status](../../backend/src/castle_qa/api/routers/annotations.py#L531) | `ReviewSessionResponse` | `200 (default)` |  |
| POST | `/api/v1/annotations/sessions/{review_id}/sync-questions` | [sync_questions](../../backend/src/castle_qa/api/routers/annotations.py#L563) | `ReviewSessionResponse` | `200 (default)` |  |
| POST | `/api/v1/annotations/reviews/{review_id}/save-persistent` | [save_review_session_persistent](../../backend/src/castle_qa/api/routers/annotations.py#L621) | `ReviewSessionResponse` | `200 (default)` | yes |
| POST | `/api/v1/annotations/sessions/{review_id}/persist` | [save_review_session_persistent](../../backend/src/castle_qa/api/routers/annotations.py#L621) | `ReviewSessionResponse` | `200 (default)` | yes |
| POST | `/api/v1/annotations/reviews/{review_id}/persist` | [save_review_session_persistent](../../backend/src/castle_qa/api/routers/annotations.py#L621) | `ReviewSessionResponse` | `200 (default)` | yes |
| POST | `/api/v1/annotations/sessions/{review_id}/save-persistent` | [save_review_session_persistent](../../backend/src/castle_qa/api/routers/annotations.py#L621) | `ReviewSessionResponse` | `200 (default)` |  |
| GET | `/api/v1/annotations/sessions/{review_id}/export/whodunnit` | [export_whodunnit_json](../../backend/src/castle_qa/api/routers/annotations.py#L652) | `handler-defined` | `200 (default)` |  |
| GET | `/api/v1/annotations/sessions/{review_id}/export/csv` | [export_whodunnit_csv](../../backend/src/castle_qa/api/routers/annotations.py#L683) | `handler-defined` | `200 (default)` |  |
| GET | `/api/v1/health` | [heal_check](../../backend/src/castle_qa/api/routers/health.py#L20) | `HealthResponse` | `200 (default)` |  |
| POST | `/api/v1/cleanup/temporary-storage` | [cleanup_temporary_storage_alias](../../backend/src/castle_qa/api/routers/health.py#L31) | `handler-defined` | `200 (default)` | yes |
| POST | `/api/v1/jobs/question-generation` | [submit_question_generation_job](../../backend/src/castle_qa/api/routers/jobs.py#L71) | `JobSubmissionResponse` | `status.HTTP_202_ACCEPTED` | yes |
| POST | `/api/v1/jobs/question-generations` | [submit_question_generation_job](../../backend/src/castle_qa/api/routers/jobs.py#L71) | `JobSubmissionResponse` | `status.HTTP_202_ACCEPTED` |  |
| POST | `/api/v1/jobs/video-understanding` | [submit_video_understanding_job](../../backend/src/castle_qa/api/routers/jobs.py#L128) | `JobSubmissionResponse` | `status.HTTP_202_ACCEPTED` | yes |
| POST | `/api/v1/jobs/video-understandings` | [submit_video_understanding_job](../../backend/src/castle_qa/api/routers/jobs.py#L128) | `JobSubmissionResponse` | `status.HTTP_202_ACCEPTED` |  |
| DELETE | `/api/v1/jobs/{job_id}` | [cancel_job](../../backend/src/castle_qa/api/routers/jobs.py#L195) | `JobStatusResponse` | `200 (default)` |  |
| GET | `/api/v1/jobs/{job_id}` | [get_job_status](../../backend/src/castle_qa/api/routers/jobs.py#L232) | `JobStatusResponse` | `200 (default)` |  |
| POST | `/api/v1/qa/videos/{video_id}/ask` | [ask_video_question](../../backend/src/castle_qa/api/routers/qa.py#L37) | `VideoQAResponse` | `200 (default)` |  |
| POST | `/api/v1/qa/analyses/{analysis_id}/ask` | [ask_analysis_question](../../backend/src/castle_qa/api/routers/qa.py#L127) | `VideoQAResponse` | `200 (default)` |  |
| POST | `/api/v1/question-generations` | [generate_question](../../backend/src/castle_qa/api/routers/questions.py#L89) | `QuestionGenerationResponse` | `status.HTTP_201_CREATED` |  |
| GET | `/api/v1/question-generations/{generation_id}` | [get_saved_generation](../../backend/src/castle_qa/api/routers/questions.py#L157) | `QuestionGenerationResponse` | `200 (default)` |  |
| POST | `/api/v1/question-generations/{generation_id}/save-persistent` | [save_question_generation_persistent](../../backend/src/castle_qa/api/routers/questions.py#L240) | `QuestionGenerationResponse` | `200 (default)` |  |
| POST | `/api/v1/videos/upload` | [upload_video](../../backend/src/castle_qa/api/routers/videos.py#L74) | `VideoDetailResponse` | `status.HTTP_201_CREATED` |  |
| POST | `/api/v1/videos/temporary-clip` | [upload_temporary_clip](../../backend/src/castle_qa/api/routers/videos.py#L129) | `VideoDetailResponse` | `status.HTTP_201_CREATED` | yes |
| POST | `/api/v1/videos/upload-clip` | [upload_temporary_clip](../../backend/src/castle_qa/api/routers/videos.py#L129) | `VideoDetailResponse` | `status.HTTP_201_CREATED` |  |
| DELETE | `/api/v1/videos/temporary-clips/{video_id}` | [delete_temporary_clip](../../backend/src/castle_qa/api/routers/videos.py#L230) | `handler-defined` | `200 (default)` |  |
| POST | `/api/v1/videos/session/{session_id}/touch` | [touch_session](../../backend/src/castle_qa/api/routers/videos.py#L253) | `handler-defined` | `200 (default)` |  |
| POST | `/api/v1/videos/cleanup-temporary` | [cleanup_temporary_media](../../backend/src/castle_qa/api/routers/videos.py#L288) | `handler-defined` | `200 (default)` |  |
| GET | `/api/v1/videos` | [list_videos](../../backend/src/castle_qa/api/routers/videos.py#L327) | `VideoListResponse` | `200 (default)` |  |
| GET | `/api/v1/videos/{video_id}` | [get_video_detail](../../backend/src/castle_qa/api/routers/videos.py#L370) | `VideoDetailResponse` | `200 (default)` |  |
| GET | `/api/v1/videos/{video_id}/stream` | [stream_video](../../backend/src/castle_qa/api/routers/videos.py#L426) | `handler-defined` | `200 (default)` |  |
| POST | `/api/v1/videos/stream-lease/{video_id}/{lease_id}/renew` | [renew_stream_lease](../../backend/src/castle_qa/api/routers/videos.py#L478) | `handler-defined` | `200 (default)` |  |
| POST | `/api/v1/videos/{video_id}/clip` | [extract_video_clip](../../backend/src/castle_qa/api/routers/videos.py#L529) | `ClipExtractionResponse` | `status.HTTP_201_CREATED` |  |

## Python implementation contracts

### backend/src/castle_qa/api/dependencies.py

- [get_job_repository, line 19](../../backend/src/castle_qa/api/dependencies.py#L19): `get_job_repository() -> JobRepository`
  Dependency provider for JobRepository.

- [get_analysis_workflow, line 24](../../backend/src/castle_qa/api/dependencies.py#L24): `get_analysis_workflow() -> AnalysisWorkflow`
  Dependency provider for AnalysisWorkflow.

- [get_question_workflow, line 37](../../backend/src/castle_qa/api/dependencies.py#L37): `get_question_workflow() -> QuestionWorkflow`
  Dependency provider for QuestionWorkflow.

- [get_video_service, line 57](../../backend/src/castle_qa/api/dependencies.py#L57): `get_video_service() -> VideoService`
  Dependency provider for VideoService.

- [get_annotation_repository, line 68](../../backend/src/castle_qa/api/dependencies.py#L68): `get_annotation_repository() -> AnnotationRepository`
  Dependency provider for AnnotationRepository.

### backend/src/castle_qa/api/main.py

- [lifespan, line 11](../../backend/src/castle_qa/api/main.py#L11): `async lifespan(app: FastAPI)`
  Application lifespan handling background maintenance tasks. Starts the periodic cleanup runner if enabled.

- [create_app, line 47](../../backend/src/castle_qa/api/main.py#L47): `create_app(enable_cleanup: bool=False) -> FastAPI`
  Create and configure the CASTLE QA Studio API.

- [run, line 115](../../backend/src/castle_qa/api/main.py#L115): `run() -> None`
  Entry point for the castle-api console script.

### backend/src/castle_qa/api/middleware/request_size_limit.py

- [RequestSizeLimitMiddleware.__init__, line 17](../../backend/src/castle_qa/api/middleware/request_size_limit.py#L17): `__init__(self, app, max_request_size_bytes: int=1040 * 1024 * 1024)`
  No docstring; inspect the linked implementation.

- [RequestSizeLimitMiddleware.dispatch, line 22](../../backend/src/castle_qa/api/middleware/request_size_limit.py#L22): `async dispatch(self, request: Request, call_next: Callable) -> Response`
  No docstring; inspect the linked implementation.

- [RequestSizeLimitMiddleware.dispatch.<locals>.limited_receive, line 59](../../backend/src/castle_qa/api/middleware/request_size_limit.py#L59): `async limited_receive()`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/api/routers/analyses.py

- [_source_temporary_metadata, line 47](../../backend/src/castle_qa/api/routers/analyses.py#L47): `_source_temporary_metadata(video_service: VideoService, analysis_id: str)`
  No docstring; inspect the linked implementation.

- [get_analysis_workflow, line 52](../../backend/src/castle_qa/api/routers/analyses.py#L52): `get_analysis_workflow() -> AnalysisWorkflow`
  Create the workflow with its repository dependency.

- [get_video_service, line 63](../../backend/src/castle_qa/api/routers/analyses.py#L63): `get_video_service() -> VideoService`
  Dependency provider for VideoService.

- [list_analyses, line 75](../../backend/src/castle_qa/api/routers/analyses.py#L75): `list_analyses(workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)]) -> AnalysisListResponse`
  Retrieve summaries of all saved video analyses.

- [merge_window_analyses, line 98](../../backend/src/castle_qa/api/routers/analyses.py#L98): `merge_window_analyses(request: MergeWindowsRequest, workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None) -> dict`
  No docstring; inspect the linked implementation.

- [get_analysis, line 221](../../backend/src/castle_qa/api/routers/analyses.py#L221): `get_analysis(analysis_id: Annotated[str, PathParameter(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> AnalysisDetailRepsonse`
  Retrieve a saved video analysis by ID, including clip-relative and source-mapped event timestamps. For temporary clip analyses, strictly enforces session token authorization.

- [save_analysis_persistent, line 355](../../backend/src/castle_qa/api/routers/analyses.py#L355): `save_analysis_persistent(analysis_id: Annotated[str, PathParameter(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> AnalysisDetailRepsonse`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/api/routers/annotations.py

- [get_annotation_repository, line 43](../../backend/src/castle_qa/api/routers/annotations.py#L43): `get_annotation_repository() -> AnnotationRepository`
  Dependency provider for AnnotationRepository.

- [get_whodunnit_adapter, line 54](../../backend/src/castle_qa/api/routers/annotations.py#L54): `get_whodunnit_adapter() -> WhodunnitExportAdapter`
  Dependency provider for WhodunnitExportAdapter.

- [_check_review_session_access, line 61](../../backend/src/castle_qa/api/routers/annotations.py#L61): `_check_review_session_access(session: AnnotationReviewSession, video_service: VideoService, effective_token: str &#124; None) -> None`
  No docstring; inspect the linked implementation.

- [_is_video_available, line 88](../../backend/src/castle_qa/api/routers/annotations.py#L88): `_is_video_available(session: AnnotationReviewSession, video_service: VideoService &#124; None=None) -> bool`
  No docstring; inspect the linked implementation.

- [_to_response, line 108](../../backend/src/castle_qa/api/routers/annotations.py#L108): `_to_response(session: AnnotationReviewSession, video_service: VideoService &#124; None=None) -> ReviewSessionResponse`
  No docstring; inspect the linked implementation.

- [_merge_questions_into_session, line 169](../../backend/src/castle_qa/api/routers/annotations.py#L169): `_merge_questions_into_session(session: AnnotationReviewSession, saved_gen_questions: list[dict[str, Any]], generation_id: str) -> int`
  Merge newly generated questions into an existing review session. Preserves all existing review decisions (accepted, edited, rejected, pending). Only appends questions that are not already present (compared by question text). Returns count of newly added questions.

- [create_or_load_session, line 220](../../backend/src/castle_qa/api/routers/annotations.py#L220): `create_or_load_session(request: CreateReviewSessionRequest, repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)], question_workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> ReviewSessionResponse`
  Initialize or retrieve a review session. For temporary clips/analyses, enforces session authorization.

- [list_sessions, line 347](../../backend/src/castle_qa/api/routers/annotations.py#L347): `list_sessions(repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> list[ReviewSessionSummary]`
  No docstring; inspect the linked implementation.

- [get_session, line 400](../../backend/src/castle_qa/api/routers/annotations.py#L400): `get_session(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> ReviewSessionResponse`
  No docstring; inspect the linked implementation.

- [update_event_review, line 423](../../backend/src/castle_qa/api/routers/annotations.py#L423): `update_event_review(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], event_index: int, request: EventReviewUpdateRequest, repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> ReviewSessionResponse`
  No docstring; inspect the linked implementation.

- [update_question_review, line 482](../../backend/src/castle_qa/api/routers/annotations.py#L482): `update_question_review(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], question_index: int, request: QuestionReviewUpdateRequest, repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> ReviewSessionResponse`
  No docstring; inspect the linked implementation.

- [update_session_status, line 531](../../backend/src/castle_qa/api/routers/annotations.py#L531): `update_session_status(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], request: SessionStatusUpdateRequest, repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> ReviewSessionResponse`
  No docstring; inspect the linked implementation.

- [sync_questions, line 563](../../backend/src/castle_qa/api/routers/annotations.py#L563): `sync_questions(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], request: SyncQuestionsRequest, repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], question_workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> ReviewSessionResponse`
  No docstring; inspect the linked implementation.

- [save_review_session_persistent, line 621](../../backend/src/castle_qa/api/routers/annotations.py#L621): `save_review_session_persistent(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> ReviewSessionResponse`
  No docstring; inspect the linked implementation.

- [export_whodunnit_json, line 652](../../backend/src/castle_qa/api/routers/annotations.py#L652): `export_whodunnit_json(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)], adapter: Annotated[WhodunnitExportAdapter, Depends(get_whodunnit_adapter)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> dict[str, Any]`
  No docstring; inspect the linked implementation.

- [export_whodunnit_csv, line 683](../../backend/src/castle_qa/api/routers/annotations.py#L683): `export_whodunnit_csv(review_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$')], repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)], adapter: Annotated[WhodunnitExportAdapter, Depends(get_whodunnit_adapter)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> Response`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/api/routers/health.py

- [heal_check, line 20](../../backend/src/castle_qa/api/routers/health.py#L20): `heal_check() -> HealthResponse`
  Check whether the Castle QA Studio API is running.

- [cleanup_temporary_storage_alias, line 31](../../backend/src/castle_qa/api/routers/health.py#L31): `cleanup_temporary_storage_alias(service: Annotated[VideoService, Depends(get_video_service)], job_repository: Annotated[JobRepository, Depends(get_job_repository)], x_internal_token: Annotated[str &#124; None, Header()]=None, authorization: Annotated[str &#124; None, Header()]=None) -> dict[str, Any]`
  Administrative cleanup route alias for /videos/cleanup-temporary.

### backend/src/castle_qa/api/routers/jobs.py

- [get_job_repository, line 52](../../backend/src/castle_qa/api/routers/jobs.py#L52): `get_job_repository() -> JobRepository`
  Create a repository using the central SQLAlchemy database configuration.

- [submit_question_generation_job, line 71](../../backend/src/castle_qa/api/routers/jobs.py#L71): `submit_question_generation_job(request: QuestionGenerationJobRequest, repository: Annotated[JobRepository, Depends(get_job_repository)], analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)]) -> JobSubmissionResponse`
  Submit a Qwen question-generation job. The endpoint saves a queued job without executing GPU inference.

- [submit_video_understanding_job, line 128](../../backend/src/castle_qa/api/routers/jobs.py#L128): `submit_video_understanding_job(request: VideoUnderstandingJobRequest, repository: Annotated[JobRepository, Depends(get_job_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> JobSubmissionResponse`
  Submit a video-understanding job. The endpoint saves a queued job without executing heavy GPU inference in FastAPI.

- [cancel_job, line 195](../../backend/src/castle_qa/api/routers/jobs.py#L195): `cancel_job(job_id: Annotated[str, PathParameter(pattern=JOB_ID_PATTERN)], repository: Annotated[JobRepository, Depends(get_job_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None) -> JobStatusResponse`
  No docstring; inspect the linked implementation.

- [get_job_status, line 232](../../backend/src/castle_qa/api/routers/jobs.py#L232): `get_job_status(job_id: Annotated[str, PathParameter(pattern=JOB_ID_PATTERN)], repository: Annotated[JobRepository, Depends(get_job_repository)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> JobStatusResponse`
  Retrieve the current state of an inference job. For temporary clip inference jobs, enforces session authorization.

### backend/src/castle_qa/api/routers/qa.py

- [get_qa_service, line 25](../../backend/src/castle_qa/api/routers/qa.py#L25): `get_qa_service() -> GroundedVideoQAService`
  Dependency provider for GroundedVideoQAService.

- [ask_video_question, line 37](../../backend/src/castle_qa/api/routers/qa.py#L37): `ask_video_question(video_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$', description='Identifier of the uploaded video')], request: AskVideoQARequest, video_service: Annotated[VideoService, Depends(get_video_service)], analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)], qa_service: Annotated[GroundedVideoQAService, Depends(get_qa_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> VideoQAResponse`
  Answer a question about a video. Returns the answer with confidence, observability determination, and supporting video timestamps. For temporary clips, strictly enforces session authorization.

- [ask_analysis_question, line 127](../../backend/src/castle_qa/api/routers/qa.py#L127): `ask_analysis_question(analysis_id: Annotated[str, PathParam(pattern='^[A-Za-z0-9][A-Za-z0-9._-]*$', description='Identifier of the video analysis')], request: AskAnalysisQARequest, analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)], qa_service: Annotated[GroundedVideoQAService, Depends(get_qa_service)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> VideoQAResponse`
  Answer a question grounded in the events and observations of a video analysis. For temporary analyses, strictly enforces session authorization.

### backend/src/castle_qa/api/routers/questions.py

- [get_question_workflow, line 50](../../backend/src/castle_qa/api/routers/questions.py#L50): `get_question_workflow() -> QuestionWorkflow`
  Create the question-generation workflow and its dependencies.

- [generate_question, line 89](../../backend/src/castle_qa/api/routers/questions.py#L89): `generate_question(request: QuestionGenerationRequest, workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)]) -> QuestionGenerationResponse`
  Generate Questions from a saved video analysis. Currently supports template generate only.

- [get_saved_generation, line 157](../../backend/src/castle_qa/api/routers/questions.py#L157): `get_saved_generation(generation_id: Annotated[str, PathParameter(pattern='^gen_[0-9a-f]{32}$')], workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)]) -> QuestionGenerationResponse`
  Retrieve previously generated questions by ID.

- [save_question_generation_persistent, line 240](../../backend/src/castle_qa/api/routers/questions.py#L240): `save_question_generation_persistent(generation_id: Annotated[str, PathParameter(pattern='^gen_[0-9a-f]{32}$')], workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)], video_service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> QuestionGenerationResponse`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/api/routers/videos.py

- [get_video_service, line 39](../../backend/src/castle_qa/api/routers/videos.py#L39): `get_video_service() -> VideoService`
  Dependency provider for the VideoService.

- [get_job_repository, line 52](../../backend/src/castle_qa/api/routers/videos.py#L52): `get_job_repository() -> JobRepository`
  Dependency provider for JobRepository.

- [_release_video_stream, line 61](../../backend/src/castle_qa/api/routers/videos.py#L61): `_release_video_stream(service: VideoService, repository: JobRepository, video_id: str, lease_id: str) -> None`
  No docstring; inspect the linked implementation.

- [upload_video, line 74](../../backend/src/castle_qa/api/routers/videos.py#L74): `upload_video(file: Annotated[UploadFile, File(description='Video file to upload')], service: Annotated[VideoService, Depends(get_video_service)]) -> VideoDetailResponse`
  Stream and validate an uploaded video file into permanent storage.

- [upload_temporary_clip, line 129](../../backend/src/castle_qa/api/routers/videos.py#L129): `upload_temporary_clip(file: Annotated[UploadFile, File(description='One extracted video clip (max 1GB, max 600s)')], service: Annotated[VideoService, Depends(get_video_service)], response: Response, session_id: Annotated[str &#124; None, Form(description='Client session identifier')]=None, session_token: Annotated[str &#124; None, Form(description='Session authorization token')]=None, x_session_id: Annotated[str &#124; None, Header(description='Session ID in header')]=None, x_session_token: Annotated[str &#124; None, Header(description='Session Token in header')]=None, source_filename: Annotated[str &#124; None, Form(description='Original local video filename (descriptive only)')]=None, source_video_ref: Annotated[str &#124; None, Form(description='Collision-resistant sourceInstanceId')]=None, source_start_seconds: Annotated[float &#124; None, Form(description='Claimed start timestamp in source video')]=None, source_end_seconds: Annotated[float &#124; None, Form(description='Claimed end timestamp in source video')]=None, source_duration_seconds: Annotated[float &#124; None, Form(description='Target interval duration')]=None, extraction_method: Annotated[str &#124; None, Form(description='Method used to extract clip')]=None, alignment_status: Annotated[str &#124; None, Form(description='Temporal alignment status')]=None, user_confirmed: Annotated[bool, Form(description='Whether user confirmed association')]=True) -> VideoDetailResponse`
  Safely stream and store one extracted clip into temporary storage. Enforces size limit (1GB) during streaming, validates duration (<=600s) with FFprobe, records source provenance metadata, and enforces the 24-hour meaningful inactivity lifecycle.

- [delete_temporary_clip, line 230](../../backend/src/castle_qa/api/routers/videos.py#L230): `delete_temporary_clip(video_id: Annotated[str, PathParam(pattern='^clip_[A-Za-z0-9_-]+$')], service: Annotated[VideoService, Depends(get_video_service)], repository: Annotated[JobRepository, Depends(get_job_repository)], x_session_token: Annotated[str &#124; None, Header(description='Temporary session token')]=None) -> dict[str, Any]`
  No docstring; inspect the linked implementation.

- [touch_session, line 253](../../backend/src/castle_qa/api/routers/videos.py#L253): `touch_session(session_id: Annotated[str, PathParam(description='ID of the session to extend')], service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header()]=None, token: Annotated[str &#124; None, Query(description='Session authorization token')]=None) -> dict[str, Any]`
  Meaningful user activity explicitly extending session expiration by 24 hours. Requires matching session token.

- [cleanup_temporary_media, line 288](../../backend/src/castle_qa/api/routers/videos.py#L288): `cleanup_temporary_media(service: Annotated[VideoService, Depends(get_video_service)], job_repository: Annotated[JobRepository, Depends(get_job_repository)], x_internal_token: Annotated[str &#124; None, Header()]=None, authorization: Annotated[str &#124; None, Header()]=None) -> dict[str, Any]`
  Purge temporary clips past their 24h retention period. Protected endpoint: requires administrative internal token. Clips needed by active jobs or active streams are protected. Permanent CASTLE dataset files are NEVER deleted.

- [list_videos, line 327](../../backend/src/castle_qa/api/routers/videos.py#L327): `list_videos(service: Annotated[VideoService, Depends(get_video_service)], session_id: Annotated[str &#124; None, Query(description='Session ID to include temporary clips')]=None, x_session_id: Annotated[str &#124; None, Header(description='Session ID header')]=None, x_session_token: Annotated[str &#124; None, Header(description='Session authorization token header')]=None, token: Annotated[str &#124; None, Query(description='Session authorization token query')]=None) -> VideoListResponse`
  List videos in library. To protect user privacy, temporary clips are NEVER returned in the global list (without session ID). Only permanent videos and (if session ID and valid token are supplied) that session's temporary clips are returned.

- [get_video_detail, line 370](../../backend/src/castle_qa/api/routers/videos.py#L370): `get_video_detail(video_id: Annotated[str, PathParam(description='ID of the video')], service: Annotated[VideoService, Depends(get_video_service)], x_session_id: Annotated[str &#124; None, Header()]=None, x_session_token: Annotated[str &#124; None, Header()]=None, token: Annotated[str &#124; None, Query(description='Session token')]=None) -> VideoDetailResponse`
  Retrieve full metadata for a specific video. For temporary clips, verifies session authorization.

- [stream_video, line 426](../../backend/src/castle_qa/api/routers/videos.py#L426): `stream_video(video_id: Annotated[str, PathParam(description='ID of the video')], service: Annotated[VideoService, Depends(get_video_service)], repository: Annotated[JobRepository, Depends(get_job_repository)], x_session_token: Annotated[str &#124; None, Header()]=None, token: Annotated[str &#124; None, Query(description='Session authorization token')]=None)`
  Stream video file directly for browser playback. Tracks an active stream lease to protect file from cleanup during active playback.

- [renew_stream_lease, line 478](../../backend/src/castle_qa/api/routers/videos.py#L478): `renew_stream_lease(video_id: Annotated[str, PathParam(description='ID of the video')], lease_id: Annotated[str, PathParam(description='ID of the active stream lease')], service: Annotated[VideoService, Depends(get_video_service)], x_session_token: Annotated[str &#124; None, Header()]=None, token: Annotated[str &#124; None, Query(description='Session authorization token')]=None, session_id: Annotated[str &#124; None, Query(description='Session authorization token alias')]=None) -> dict[str, Any]`
  Extends the TTL of an ongoing video stream lease. Verifies session authorization for temporary video clips.

- [extract_video_clip, line 529](../../backend/src/castle_qa/api/routers/videos.py#L529): `extract_video_clip(video_id: Annotated[str, PathParam(description='ID of the video')], request: ClipExtractionRequest, service: Annotated[VideoService, Depends(get_video_service)]) -> ClipExtractionResponse`
  Extract a temporal clip centered around a given timestamp.

### backend/src/castle_qa/application/analysis_workflow.py

- [AnalysisWorkflow.__init__, line 11](../../backend/src/castle_qa/application/analysis_workflow.py#L11): `__init__(self, repository: VideoAnalysisRepository)`
  No docstring; inspect the linked implementation.

- [AnalysisWorkflow.list_analyses, line 17](../../backend/src/castle_qa/application/analysis_workflow.py#L17): `list_analyses(self) -> list[tuple[str, VideoAnalysis]]`
  Retrieve all saved analyses with their IDs.

- [AnalysisWorkflow.get_analysis, line 39](../../backend/src/castle_qa/application/analysis_workflow.py#L39): `get_analysis(self, analysis_id: str) -> VideoAnalysis &#124; None`
  Retrieve a single saved analysis by ID.

### backend/src/castle_qa/application/question_workflow.py

- [QuestionWorkflow.__init__, line 40](../../backend/src/castle_qa/application/question_workflow.py#L40): `__init__(self, analysis_repository: VideoAnalysisRepository, question_repository: QuestionRepository, generator: QuestionGenerationService, validator: QuestionValidator, generator_name: str='template')`
  No docstring; inspect the linked implementation.

- [QuestionWorkflow.generate, line 54](../../backend/src/castle_qa/application/question_workflow.py#L54): `generate(self, analysis_id: str, criteria: QACriteria, clip_duration_seconds: float, *, create_generation_record: bool=False) -> QuestionGenerationResult &#124; None`
  Load an analysis, generate questions, validate, save, and return the result. Returns None when the analysis does not exist.

- [QuestionWorkflow.get_saved_generation, line 124](../../backend/src/castle_qa/application/question_workflow.py#L124): `get_saved_generation(self, generation_id: str) -> dict &#124; None`
  Retrieve a saved question-generation result. Returns None when the generation does not exist. Does not run the question generator.

- [QuestionWorkflow.make_persistent, line 138](../../backend/src/castle_qa/application/question_workflow.py#L138): `make_persistent(self, generation_id: str) -> dict &#124; None`
  Mark a question-generation result persistent.

### backend/src/castle_qa/application/video_understanding_workflow.py

- [VideoUnderstandingWorkflow.__init__, line 31](../../backend/src/castle_qa/application/video_understanding_workflow.py#L31): `__init__(self, service: VideoUnderstandingService, repository: VideoAnalysisRepository, probe: VideoProbe &#124; None=None)`
  No docstring; inspect the linked implementation.

- [VideoUnderstandingWorkflow.analyze_video, line 41](../../backend/src/castle_qa/application/video_understanding_workflow.py#L41): `analyze_video(self, video_path: Path, *, clip_start: str='00:00:00', clip_end: str &#124; None=None, duration_seconds: float &#124; None=None, source_metadata: dict &#124; None=None) -> VideoUnderstandingResult`
  Execute video understanding on a video file and save the structured analysis.

### backend/src/castle_qa/config/api_settings.py

- [_find_repo_root, line 6](../../backend/src/castle_qa/config/api_settings.py#L6): `_find_repo_root() -> Path`
  No docstring; inspect the linked implementation.

- [resolve_data_directory, line 15](../../backend/src/castle_qa/config/api_settings.py#L15): `resolve_data_directory(environment_variable: str, default_directory: str) -> Path`
  Resolve a configured storage directory. Relative paths are resolved from the project root. Absolute paths are supported for Docker deployments.

- [APISettings.is_insecure_default_cleanup_token, line 58](../../backend/src/castle_qa/config/api_settings.py#L58): `is_insecure_default_cleanup_token(self) -> bool`
  No docstring; inspect the linked implementation.

- [APISettings.from_environment, line 62](../../backend/src/castle_qa/config/api_settings.py#L62): `from_environment(cls) -> 'APISettings'`
  Create API settings from environment variables.

### backend/src/castle_qa/config/settings.py

- [Settings.from_environment, line 27](../../backend/src/castle_qa/config/settings.py#L27): `from_environment(cls) -> 'Settings'`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/deployment/readiness_check.py

- [check_python_environment, line 18](../../backend/src/castle_qa/deployment/readiness_check.py#L18): `check_python_environment() -> Dict[str, Any]`
  Check Python version and core runtime libraries.

- [check_ffmpeg, line 31](../../backend/src/castle_qa/deployment/readiness_check.py#L31): `check_ffmpeg() -> Dict[str, Any]`
  Check availability of FFmpeg and FFprobe on PATH.

- [check_castle_dataset, line 70](../../backend/src/castle_qa/deployment/readiness_check.py#L70): `check_castle_dataset(project_root: Path) -> Dict[str, Any]`
  Check existence and size of golden CASTLE dataset video.

- [check_directories_and_storage, line 88](../../backend/src/castle_qa/deployment/readiness_check.py#L88): `check_directories_and_storage(project_root: Path) -> List[Dict[str, Any]]`
  Check required data directories, accessibility, and disk space.

- [check_configuration_and_security, line 135](../../backend/src/castle_qa/deployment/readiness_check.py#L135): `check_configuration_and_security() -> List[Dict[str, Any]]`
  Validate environment settings and security configurations.

- [check_inference_mode_and_gpu, line 170](../../backend/src/castle_qa/deployment/readiness_check.py#L170): `check_inference_mode_and_gpu() -> List[Dict[str, Any]]`
  Validate inference mode and check NVIDIA CUDA availability when relevant.

- [run_all_checks, line 276](../../backend/src/castle_qa/deployment/readiness_check.py#L276): `run_all_checks(project_root: Path &#124; None=None) -> Tuple[List[Dict[str, Any]], bool, bool]`
  Run all readiness checks and return results, overall pass status, and blocked status.

- [print_readiness_report, line 302](../../backend/src/castle_qa/deployment/readiness_check.py#L302): `print_readiness_report()`
  Print formatted terminal report.

### backend/src/castle_qa/domain/annotation_review.py

- [EventReviewItem.get_effective_start, line 47](../../backend/src/castle_qa/domain/annotation_review.py#L47): `get_effective_start(self) -> float`
  No docstring; inspect the linked implementation.

- [EventReviewItem.get_effective_end, line 54](../../backend/src/castle_qa/domain/annotation_review.py#L54): `get_effective_end(self) -> float`
  No docstring; inspect the linked implementation.

- [EventReviewItem.get_effective_description, line 61](../../backend/src/castle_qa/domain/annotation_review.py#L61): `get_effective_description(self) -> str`
  No docstring; inspect the linked implementation.

- [EventReviewItem.get_effective_actor, line 64](../../backend/src/castle_qa/domain/annotation_review.py#L64): `get_effective_actor(self) -> str &#124; None`
  No docstring; inspect the linked implementation.

- [EventReviewItem.to_dict, line 67](../../backend/src/castle_qa/domain/annotation_review.py#L67): `to_dict(self) -> dict[str, Any]`
  No docstring; inspect the linked implementation.

- [EventReviewItem.from_dict, line 73](../../backend/src/castle_qa/domain/annotation_review.py#L73): `from_dict(cls, data: dict[str, Any]) -> 'EventReviewItem'`
  No docstring; inspect the linked implementation.

- [QuestionReviewItem.get_effective_question, line 122](../../backend/src/castle_qa/domain/annotation_review.py#L122): `get_effective_question(self) -> str`
  No docstring; inspect the linked implementation.

- [QuestionReviewItem.get_effective_answer, line 125](../../backend/src/castle_qa/domain/annotation_review.py#L125): `get_effective_answer(self) -> str &#124; None`
  No docstring; inspect the linked implementation.

- [QuestionReviewItem.to_dict, line 128](../../backend/src/castle_qa/domain/annotation_review.py#L128): `to_dict(self) -> dict[str, Any]`
  No docstring; inspect the linked implementation.

- [QuestionReviewItem.from_dict, line 134](../../backend/src/castle_qa/domain/annotation_review.py#L134): `from_dict(cls, data: dict[str, Any]) -> 'QuestionReviewItem'`
  No docstring; inspect the linked implementation.

- [AnnotationReviewSession.mock_notice, line 187](../../backend/src/castle_qa/domain/annotation_review.py#L187): `mock_notice(self) -> str &#124; None`
  No docstring; inspect the linked implementation.

- [AnnotationReviewSession.create, line 195](../../backend/src/castle_qa/domain/annotation_review.py#L195): `create(cls, analysis_id: str, video_id: str &#124; None=None, generation_id: str &#124; None=None, summary: str='', events: list[EventReviewItem] &#124; None=None, questions: list[QuestionReviewItem] &#124; None=None, reviewer_id: str &#124; None=None, is_persistent: bool=False, is_mock: bool=False, inference_mode: str='real') -> 'AnnotationReviewSession'`
  No docstring; inspect the linked implementation.

- [AnnotationReviewSession.to_dict, line 226](../../backend/src/castle_qa/domain/annotation_review.py#L226): `to_dict(self) -> dict[str, Any]`
  No docstring; inspect the linked implementation.

- [AnnotationReviewSession.from_dict, line 245](../../backend/src/castle_qa/domain/annotation_review.py#L245): `from_dict(cls, data: dict[str, Any]) -> 'AnnotationReviewSession'`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/domain/clip_request.py

- [ClipRequest.__post_init__, line 17](../../backend/src/castle_qa/domain/clip_request.py#L17): `__post_init__(self)`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/domain/clip_result.py

- [ClipResult.to_dict, line 19](../../backend/src/castle_qa/domain/clip_result.py#L19): `to_dict(self) -> dict`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/domain/event.py

- [Event.to_dict, line 17](../../backend/src/castle_qa/domain/event.py#L17): `to_dict(self) -> dict`
  No docstring; inspect the linked implementation.

- [Event.from_dict, line 21](../../backend/src/castle_qa/domain/event.py#L21): `from_dict(cls, data: dict) -> 'Event'`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/domain/grounded_qa.py

- [EvidenceInterval.to_dict, line 14](../../backend/src/castle_qa/domain/grounded_qa.py#L14): `to_dict(self) -> dict[str, Any]`
  No docstring; inspect the linked implementation.

- [EvidenceInterval.from_dict, line 18](../../backend/src/castle_qa/domain/grounded_qa.py#L18): `from_dict(cls, data: dict[str, Any]) -> 'EvidenceInterval'`
  No docstring; inspect the linked implementation.

- [VideoQAAnswer.to_dict, line 44](../../backend/src/castle_qa/domain/grounded_qa.py#L44): `to_dict(self) -> dict[str, Any]`
  No docstring; inspect the linked implementation.

- [VideoQAAnswer.from_dict, line 61](../../backend/src/castle_qa/domain/grounded_qa.py#L61): `from_dict(cls, data: dict[str, Any]) -> 'VideoQAAnswer'`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/domain/inference_job.py

- [InferenceJob.new_question_generation, line 45](../../backend/src/castle_qa/domain/inference_job.py#L45): `new_question_generation(cls, analysis_id: str, clip_duration_seconds: float, max_questions: int=5, criteria_text: str='') -> 'InferenceJob'`
  Create a queued Qwen question-generation job.

- [InferenceJob.new_video_understanding, line 93](../../backend/src/castle_qa/domain/inference_job.py#L93): `new_video_understanding(cls, video_id: str, video_path: str, fps: float=2.0, max_new_tokens: int=1024, source_metadata: dict[str, Any] &#124; None=None, session_id: str &#124; None=None) -> 'InferenceJob'`
  Create a queued video-understanding job.

### backend/src/castle_qa/domain/qa_criteria.py

- [requested_question_starter, line 25](../../backend/src/castle_qa/domain/qa_criteria.py#L25): `requested_question_starter(text: str) -> str &#124; None`
  Extract a small, safe style preference from freeform criteria.

- [QACriteria.question_starter, line 46](../../backend/src/castle_qa/domain/qa_criteria.py#L46): `question_starter(self) -> str &#124; None`
  No docstring; inspect the linked implementation.

- [QACriteria.__post_init__, line 52](../../backend/src/castle_qa/domain/qa_criteria.py#L52): `__post_init__(self) -> None`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/domain/question_candidate.py

- [QuestionCandidate.to_dict, line 20](../../backend/src/castle_qa/domain/question_candidate.py#L20): `to_dict(self) -> dict`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/domain/video_analysis.py

- [VideoAnalysis.mock_notice, line 31](../../backend/src/castle_qa/domain/video_analysis.py#L31): `mock_notice(self) -> Optional[str]`
  No docstring; inspect the linked implementation.

- [VideoAnalysis.to_dict, line 38](../../backend/src/castle_qa/domain/video_analysis.py#L38): `to_dict(self) -> dict`
  No docstring; inspect the linked implementation.

- [VideoAnalysis.from_dict, line 61](../../backend/src/castle_qa/domain/video_analysis.py#L61): `from_dict(cls, data: dict, clip_path: Path, model_name: str) -> 'VideoAnalysis'`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/infrastructure/database/session.py

- [resolve_job_database_path, line 13](../../backend/src/castle_qa/infrastructure/database/session.py#L13): `resolve_job_database_path() -> Path`
  Resolve the SQLite database path relative to the project root when a relative path is used.

- [get_db_session, line 59](../../backend/src/castle_qa/infrastructure/database/session.py#L59): `get_db_session() -> Iterator[Session]`
  Yield a database session and close it when the operation finishes.

### backend/src/castle_qa/infrastructure/repositories/annotation_repository.py

- [AnnotationRepository.__init__, line 17](../../backend/src/castle_qa/infrastructure/repositories/annotation_repository.py#L17): `__init__(self, directory: Path)`
  No docstring; inspect the linked implementation.

- [AnnotationRepository.save, line 21](../../backend/src/castle_qa/infrastructure/repositories/annotation_repository.py#L21): `save(self, session: AnnotationReviewSession) -> Path`
  Atomically save an annotation review session.

- [AnnotationRepository.load, line 47](../../backend/src/castle_qa/infrastructure/repositories/annotation_repository.py#L47): `load(self, review_id: str) -> AnnotationReviewSession &#124; None`
  Load an annotation review session by its ID.

- [AnnotationRepository.find_by_analysis, line 66](../../backend/src/castle_qa/infrastructure/repositories/annotation_repository.py#L66): `find_by_analysis(self, analysis_id: str) -> AnnotationReviewSession &#124; None`
  Find the most recent review session for a given analysis_id.

- [AnnotationRepository.list_sessions, line 90](../../backend/src/castle_qa/infrastructure/repositories/annotation_repository.py#L90): `list_sessions(self) -> list[AnnotationReviewSession]`
  List all saved review sessions.

### backend/src/castle_qa/infrastructure/repositories/job_repository.py

- [JobRepository.__init__, line 27](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L27): `__init__(self, database_path: Path &#124; None=None)`
  No docstring; inspect the linked implementation.

- [JobRepository._validate_job_id, line 76](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L76): `_validate_job_id(job_id: str) -> None`
  No docstring; inspect the linked implementation.

- [JobRepository._utc_now, line 84](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L84): `_utc_now() -> str`
  No docstring; inspect the linked implementation.

- [JobRepository._to_domain, line 90](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L90): `_to_domain(record: InferenceJobORM) -> InferenceJob`
  Convert an ORM record into a domain model.

- [JobRepository.create, line 112](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L112): `create(self, job: InferenceJob) -> None`
  Save a new queued inference job.

- [JobRepository.get, line 139](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L139): `get(self, job_id: str) -> InferenceJob &#124; None`
  Retrive an inference job by ID.

- [JobRepository.find_potentially_stale_running, line 161](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L161): `find_potentially_stale_running(self, *, older_than_seconds: float, now: datetime &#124; None=None) -> list[InferenceJob]`
  Find running jobs older than a specified threshold. This method is READ-ONLY. It does not: - Change job statuses. - Retry inference. - Requeue jobs. - Assume a worker has crashed. A job may be old but still actively processing.

- [JobRepository.claim_next, line 262](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L262): `claim_next(self, worker_id: str &#124; None=None) -> InferenceJob &#124; None`
  Atomically claim the oldest queued job. Uses a single UPDATE ... RETURNING statement to prevent duplicate job claims.

- [JobRepository.heartbeat, line 315](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L315): `heartbeat(self, job_id: str, claim_token: str) -> bool`
  Record a heartbeat for an active running job. Only succeeds if the job is running and the claim_token matches.

- [JobRepository.mark_completed, line 342](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L342): `mark_completed(self, job_id: str, result_id: str, claim_token: str &#124; None=None) -> bool`
  Mark a running job as completed. If claim_token is provided, validates that the caller owns the active claim.

- [JobRepository.request_cancel, line 383](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L383): `request_cancel(self, job_id: str) -> InferenceJob &#124; None`
  Cancel queued work or request safe cancellation after a running worker releases media.

- [JobRepository.is_cancel_requested, line 404](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L404): `is_cancel_requested(self, job_id: str) -> bool`
  No docstring; inspect the linked implementation.

- [JobRepository.mark_failed, line 409](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L409): `mark_failed(self, job_id: str, error_message: str, claim_token: str &#124; None=None) -> bool`
  Mark a running job as failed. If claim_token is provided, validates that the caller owns the active claim.

- [JobRepository.recover_stale_jobs, line 449](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L449): `recover_stale_jobs(self, *, stale_threshold_seconds: float=60.0, max_attempts: int=3, now: datetime &#124; None=None) -> list[InferenceJob]`
  Identify and recover running jobs whose workers have crashed or stopped heartbeating. If attempt_count < max_attempts, re-queue the job. If attempt_count >= max_attempts, mark the job as FAILED.

- [JobRepository.has_active_jobs_for_video, line 540](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L540): `has_active_jobs_for_video(self, video_id: str) -> bool`
  Check whether there are any queued or running jobs associated with video_id. Protects media from premature lifecycle cleanup while active jobs depend on it.

- [JobRepository.close, line 556](../../backend/src/castle_qa/infrastructure/repositories/job_repository.py#L556): `close(self) -> None`
  Dispose of an engine owned by this repository. The central application engine is not disposed.

### backend/src/castle_qa/infrastructure/repositories/metadata_repository.py

- [MetadataRepository.__init__, line 7](../../backend/src/castle_qa/infrastructure/repositories/metadata_repository.py#L7): `__init__(self, directory: Path)`
  No docstring; inspect the linked implementation.

- [MetadataRepository.save, line 12](../../backend/src/castle_qa/infrastructure/repositories/metadata_repository.py#L12): `save(self, result: ClipResult) -> Path`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/infrastructure/repositories/question_repository.py

- [QuestionRepository.__init__, line 15](../../backend/src/castle_qa/infrastructure/repositories/question_repository.py#L15): `__init__(self, output_directory: Path)`
  No docstring; inspect the linked implementation.

- [QuestionRepository._validate_generation_id, line 24](../../backend/src/castle_qa/infrastructure/repositories/question_repository.py#L24): `_validate_generation_id(generation_id: str) -> None`
  Validate a generation identifier.

- [QuestionRepository.save, line 37](../../backend/src/castle_qa/infrastructure/repositories/question_repository.py#L37): `save(self, analysis: VideoAnalysis, criteria: QACriteria, questions: list[QuestionCandidate], generation_id: str &#124; None=None, analysis_id: str &#124; None=None, generator: str &#124; None=None) -> Path`
  No docstring; inspect the linked implementation.

- [QuestionRepository.load, line 107](../../backend/src/castle_qa/infrastructure/repositories/question_repository.py#L107): `load(self, generation_id: str) -> dict &#124; None`
  Load a saved question-generation result. Returns None if the result does not exist.

- [QuestionRepository.make_persistent, line 146](../../backend/src/castle_qa/infrastructure/repositories/question_repository.py#L146): `make_persistent(self, generation_id: str) -> dict &#124; None`
  Mark a question-generation result as persistent so it survives cleanup.

### backend/src/castle_qa/infrastructure/repositories/video_analysis_repository.py

- [VideoAnalysisRepository.__init__, line 9](../../backend/src/castle_qa/infrastructure/repositories/video_analysis_repository.py#L9): `__init__(self, directory: Path)`
  No docstring; inspect the linked implementation.

- [VideoAnalysisRepository.save, line 16](../../backend/src/castle_qa/infrastructure/repositories/video_analysis_repository.py#L16): `save(self, analysis: VideoAnalysis) -> Path`
  Save a VideoAnalysis as a JSON file.

- [VideoAnalysisRepository.list_ids, line 43](../../backend/src/castle_qa/infrastructure/repositories/video_analysis_repository.py#L43): `list_ids(self, include_temporary: bool=False) -> list[str]`
  List available analysis IDs. By default, excludes temporary clip analyses (starting with 'clip_') to protect user privacy and keep the global repository clean.

- [VideoAnalysisRepository.load, line 70](../../backend/src/castle_qa/infrastructure/repositories/video_analysis_repository.py#L70): `load(self, analysis_id: str) -> VideoAnalysis &#124; None`
  Load a saved analysis by ID.

### backend/src/castle_qa/integrations/whodunnit_export_adapter.py

- [WhodunnitExportAdapter.__init__, line 37](../../backend/src/castle_qa/integrations/whodunnit_export_adapter.py#L37): `__init__(self, config: WhodunnitExportConfig &#124; None=None)`
  No docstring; inspect the linked implementation.

- [WhodunnitExportAdapter.config, line 41](../../backend/src/castle_qa/integrations/whodunnit_export_adapter.py#L41): `config(self) -> WhodunnitExportConfig`
  No docstring; inspect the linked implementation.

- [WhodunnitExportAdapter.export_json, line 44](../../backend/src/castle_qa/integrations/whodunnit_export_adapter.py#L44): `export_json(self, session: AnnotationReviewSession, all_participants: list[str] &#124; None=None) -> dict[str, Any]`
  Export reviewed items into Whodunnit JSON package.

- [WhodunnitExportAdapter.export_csv, line 163](../../backend/src/castle_qa/integrations/whodunnit_export_adapter.py#L163): `export_csv(self, session: AnnotationReviewSession) -> str`
  Export reviewed items to CSV tabular representation.

### backend/src/castle_qa/services/cleanup_runner.py

- [CleanupReport.to_dict, line 33](../../backend/src/castle_qa/services/cleanup_runner.py#L33): `to_dict(self) -> dict`
  No docstring; inspect the linked implementation.

- [TemporaryStorageCleanupRunner.__init__, line 55](../../backend/src/castle_qa/services/cleanup_runner.py#L55): `__init__(self, session_service: TemporarySessionService, temporary_dir: Path, job_repository: Optional[Any]=None, stream_tracker: Optional[StreamLeaseTracker]=None, analysis_dir: Optional[Path]=None, question_dir: Optional[Path]=None, review_dir: Optional[Path]=None, interval_seconds: int=3600)`
  No docstring; inspect the linked implementation.

- [TemporaryStorageCleanupRunner._safe_unlink, line 79](../../backend/src/castle_qa/services/cleanup_runner.py#L79): `_safe_unlink(self, file_path: Path, report: CleanupReport, dry_run: bool) -> bool`
  Safely delete a file only if it exists within the managed temporary directory or explicitly managed session artifact paths. Never touches permanent datasets.

- [TemporaryStorageCleanupRunner.run_once, line 136](../../backend/src/castle_qa/services/cleanup_runner.py#L136): `run_once(self, dry_run: bool=False) -> CleanupReport`
  Execute a single, idempotent cleanup cycle across all temporary sessions.

- [TemporaryStorageCleanupRunner.start_background_loop, line 282](../../backend/src/castle_qa/services/cleanup_runner.py#L282): `start_background_loop(self) -> None`
  Start the background periodic cleanup thread.

- [TemporaryStorageCleanupRunner.start_background_loop.<locals>._loop, line 291](../../backend/src/castle_qa/services/cleanup_runner.py#L291): `_loop()`
  No docstring; inspect the linked implementation.

- [TemporaryStorageCleanupRunner.stop_background_loop, line 308](../../backend/src/castle_qa/services/cleanup_runner.py#L308): `stop_background_loop(self) -> None`
  Signal the background thread to stop and wait for it to join.

### backend/src/castle_qa/services/question_generation/question_generation_service.py

- [QuestionGenerationService.generate, line 10](../../backend/src/castle_qa/services/question_generation/question_generation_service.py#L10): `generate(self, analysis: VideoAnalysis, criteria: QACriteria) -> list[QuestionCandidate]`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/question_generation/question_validator.py

- [QuestionValidator.validate, line 8](../../backend/src/castle_qa/services/question_generation/question_validator.py#L8): `validate(self, candidates: list[QuestionCandidate], criteria: QACriteria, clip_duration_seconds: float &#124; None=None) -> list[QuestionCandidate]`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py

- [QwenLocalQuestionGenerator.__init__, line 31](../../backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py#L31): `__init__(self, model_name: str='Qwen/Qwen2.5-VL-7B-Instruct', prompt_path: Path=Path('prompts/question_generation.txt'), raw_output_dir: Path=Path('data/questions/raw'), max_new_tokens: int=768, text_generator: Callable[[str], str] &#124; None=None) -> None`
  No docstring; inspect the linked implementation.

- [QwenLocalQuestionGenerator.generate, line 64](../../backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py#L64): `generate(self, analysis: VideoAnalysis, criteria: QACriteria) -> list[QuestionCandidate]`
  No docstring; inspect the linked implementation.

- [QwenLocalQuestionGenerator._question_is_grounded, line 217](../../backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py#L217): `_question_is_grounded(cls, question: str, event) -> bool`
  Reject question wording that adds content absent from its event.

- [QwenLocalQuestionGenerator._question_is_grounded.<locals>.content_terms, line 220](../../backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py#L220): `content_terms(text: str) -> set[str]`
  No docstring; inspect the linked implementation.

- [QwenLocalQuestionGenerator.parse_response, line 243](../../backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py#L243): `parse_response(raw_response: str) -> list[dict]`
  No docstring; inspect the linked implementation.

- [QwenLocalQuestionGenerator._generate_text, line 302](../../backend/src/castle_qa/services/question_generation/qwen_local_question_generator.py#L302): `_generate_text(self, prompt: str) -> str`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/question_generation/template_question_generator.py

- [TemplateQuestionGenerator.generate, line 17](../../backend/src/castle_qa/services/question_generation/template_question_generator.py#L17): `generate(self, analysis: VideoAnalysis, criteria: QACriteria) -> list[QuestionCandidate]`
  No docstring; inspect the linked implementation.

- [TemplateQuestionGenerator._criteria_terms, line 101](../../backend/src/castle_qa/services/question_generation/template_question_generator.py#L101): `_criteria_terms(text: str) -> set[str]`
  No docstring; inspect the linked implementation.

- [TemplateQuestionGenerator._format_timestamp, line 114](../../backend/src/castle_qa/services/question_generation/template_question_generator.py#L114): `_format_timestamp(seconds: float) -> str`
  No docstring; inspect the linked implementation.

- [TemplateQuestionGenerator._question_from_description, line 120](../../backend/src/castle_qa/services/question_generation/template_question_generator.py#L120): `_question_from_description(self, actor: str &#124; None, description: str, question_starter: str &#124; None='who') -> str &#124; None`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/stream_tracker.py

- [StreamLeaseTracker.__init__, line 21](../../backend/src/castle_qa/services/stream_tracker.py#L21): `__init__(self, leases_dir: Optional[Path]=None, lease_ttl_seconds: float=300.0)`
  No docstring; inspect the linked implementation.

- [StreamLeaseTracker.set_leases_dir, line 29](../../backend/src/castle_qa/services/stream_tracker.py#L29): `set_leases_dir(self, leases_dir: Path) -> None`
  No docstring; inspect the linked implementation.

- [StreamLeaseTracker.acquire, line 33](../../backend/src/castle_qa/services/stream_tracker.py#L33): `acquire(self, video_id: str) -> str`
  Record the start of a video stream for video_id. Returns a unique lease ID.

- [StreamLeaseTracker.release, line 64](../../backend/src/castle_qa/services/stream_tracker.py#L64): `release(self, video_id: str, lease_id: Optional[str]=None) -> int`
  Record the completion or termination of a video stream for video_id. Returns the remaining count of active streams for this video.

- [StreamLeaseTracker.touch_lease, line 93](../../backend/src/castle_qa/services/stream_tracker.py#L93): `touch_lease(self, video_id: str, lease_id: str) -> bool`
  Extend the TTL of an active file-backed lease by updating its timestamp and mtime. Returns True if the lease exists and was renewed, False otherwise.

- [StreamLeaseTracker.has_active_streams, line 120](../../backend/src/castle_qa/services/stream_tracker.py#L120): `has_active_streams(self, video_id: str) -> bool`
  Check if video_id is currently being streamed by one or more clients across any worker process.

- [StreamLeaseTracker.active_stream_count, line 151](../../backend/src/castle_qa/services/stream_tracker.py#L151): `active_stream_count(self, video_id: str) -> int`
  Return the number of concurrent active streams for video_id across all workers.

- [StreamLeaseTracker.total_active_streams, line 173](../../backend/src/castle_qa/services/stream_tracker.py#L173): `total_active_streams(self) -> int`
  Return total active streams across all videos.

- [StreamLeaseTracker.reset_for_testing, line 194](../../backend/src/castle_qa/services/stream_tracker.py#L194): `reset_for_testing(self) -> None`
  Clear all active stream records (for test isolation).

### backend/src/castle_qa/services/temporary_session_service.py

- [TemporarySession.to_dict, line 30](../../backend/src/castle_qa/services/temporary_session_service.py#L30): `to_dict(self) -> dict`
  No docstring; inspect the linked implementation.

- [TemporarySession.from_dict, line 34](../../backend/src/castle_qa/services/temporary_session_service.py#L34): `from_dict(cls, data: dict) -> 'TemporarySession'`
  No docstring; inspect the linked implementation.

- [TemporarySessionService.__init__, line 55](../../backend/src/castle_qa/services/temporary_session_service.py#L55): `__init__(self, base_dir: Path, now_fn: Optional[Callable[[], datetime]]=None, retention_hours: int=24)`
  No docstring; inspect the linked implementation.

- [TemporarySessionService._now, line 66](../../backend/src/castle_qa/services/temporary_session_service.py#L66): `_now(self) -> datetime`
  No docstring; inspect the linked implementation.

- [TemporarySessionService._get_session_path, line 72](../../backend/src/castle_qa/services/temporary_session_service.py#L72): `_get_session_path(self, session_id: str) -> Path`
  No docstring; inspect the linked implementation.

- [TemporarySessionService._save_session_atomic, line 76](../../backend/src/castle_qa/services/temporary_session_service.py#L76): `_save_session_atomic(self, session: TemporarySession) -> None`
  No docstring; inspect the linked implementation.

- [TemporarySessionService.create_session, line 101](../../backend/src/castle_qa/services/temporary_session_service.py#L101): `create_session(self, session_id: Optional[str]=None, session_token: Optional[str]=None, retention_hours: Optional[int]=None) -> TemporarySession`
  Create a new durable temporary session with an unguessable token.

- [TemporarySessionService.get_session, line 130](../../backend/src/castle_qa/services/temporary_session_service.py#L130): `get_session(self, session_id: str) -> Optional[TemporarySession]`
  Retrieve an existing temporary session by ID.

- [TemporarySessionService.validate_token, line 145](../../backend/src/castle_qa/services/temporary_session_service.py#L145): `validate_token(self, session_id: str, session_token: Optional[str]) -> bool`
  Validate that the provided session_token matches the session record. Uses constant-time comparison to prevent timing attacks.

- [TemporarySessionService.find_session_for_clip, line 157](../../backend/src/castle_qa/services/temporary_session_service.py#L157): `find_session_for_clip(self, clip_id: str) -> Optional[TemporarySession]`
  No docstring; inspect the linked implementation.

- [TemporarySessionService.find_session_for_analysis, line 163](../../backend/src/castle_qa/services/temporary_session_service.py#L163): `find_session_for_analysis(self, analysis_id: str) -> Optional[TemporarySession]`
  No docstring; inspect the linked implementation.

- [TemporarySessionService.find_session_for_question, line 169](../../backend/src/castle_qa/services/temporary_session_service.py#L169): `find_session_for_question(self, question_id: str) -> Optional[TemporarySession]`
  No docstring; inspect the linked implementation.

- [TemporarySessionService.find_session_for_review, line 175](../../backend/src/castle_qa/services/temporary_session_service.py#L175): `find_session_for_review(self, review_id: str) -> Optional[TemporarySession]`
  No docstring; inspect the linked implementation.

- [TemporarySessionService.record_activity, line 181](../../backend/src/castle_qa/services/temporary_session_service.py#L181): `record_activity(self, session_id: str, action: str, retention_hours: Optional[int]=None) -> Optional[TemporarySession]`
  Record a meaningful user activity, extending the session expiry by 24 hours. Meaningful actions: clip upload, starting analysis, generating QA, editing reviews, explicit touch. Background polling or cleanup checks MUST NOT call this method.

- [TemporarySessionService.register_resource, line 219](../../backend/src/castle_qa/services/temporary_session_service.py#L219): `register_resource(self, session_id: str, clip_id: Optional[str]=None, analysis_id: Optional[str]=None, question_id: Optional[str]=None, review_id: Optional[str]=None) -> Optional[TemporarySession]`
  Associate temporary resources (clip, analysis, question, review) with a session. Ensures all session artifacts are purged together during cleanup.

- [TemporarySessionService.make_persistent, line 253](../../backend/src/castle_qa/services/temporary_session_service.py#L253): `make_persistent(self, analysis_id: Optional[str]=None, review_id: Optional[str]=None, question_id: Optional[str]=None) -> bool`
  Mark an analysis or review session as explicitly persistent, removing it from the automatic purge list so it will survive beyond 24h inactivity.

- [TemporarySessionService.is_session_expired, line 280](../../backend/src/castle_qa/services/temporary_session_service.py#L280): `is_session_expired(self, session: TemporarySession) -> bool`
  Check if a session has passed its inactivity expiration threshold.

- [TemporarySessionService.acquire_cleanup_lease, line 293](../../backend/src/castle_qa/services/temporary_session_service.py#L293): `acquire_cleanup_lease(self, session_id: str) -> bool`
  Atomically transition session state to 'cleaning'. Prevents races with new job submissions or file accesses while cleanup runs. Returns True if the lease was successfully acquired, False otherwise.

- [TemporarySessionService.release_cleanup_lease, line 317](../../backend/src/castle_qa/services/temporary_session_service.py#L317): `release_cleanup_lease(self, session_id: str) -> None`
  Release cleanup lease and restore session to 'active' if cleanup was aborted.

- [TemporarySessionService.mark_purged, line 327](../../backend/src/castle_qa/services/temporary_session_service.py#L327): `mark_purged(self, session_id: str) -> None`
  Mark session as purged and unlink the session record.

- [TemporarySessionService.list_all_sessions, line 336](../../backend/src/castle_qa/services/temporary_session_service.py#L336): `list_all_sessions(self) -> List[TemporarySession]`
  List all tracked sessions.

### backend/src/castle_qa/services/video_clip_extractor.py

- [VideoClipExtractor.__init__, line 10](../../backend/src/castle_qa/services/video_clip_extractor.py#L10): `__init__(self, video_probe: VideoProbe=None, output_dir: Path=None)`
  No docstring; inspect the linked implementation.

- [VideoClipExtractor.extract, line 16](../../backend/src/castle_qa/services/video_clip_extractor.py#L16): `extract(self, request: ClipRequest) -> ClipResult`
  No docstring; inspect the linked implementation.

- [VideoClipExtractor._build_output_path, line 53](../../backend/src/castle_qa/services/video_clip_extractor.py#L53): `_build_output_path(self, request: ClipRequest) -> Path`
  No docstring; inspect the linked implementation.

- [VideoClipExtractor._run_ffmpeg, line 68](../../backend/src/castle_qa/services/video_clip_extractor.py#L68): `_run_ffmpeg(video_path: Path, output_path: Path, start: float, duration: float) -> None`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/video_probe.py

- [VideoProbe.get_duration, line 25](../../backend/src/castle_qa/services/video_probe.py#L25): `get_duration(self, video_path: Path) -> float`
  No docstring; inspect the linked implementation.

- [VideoProbe.get_metadata, line 29](../../backend/src/castle_qa/services/video_probe.py#L29): `get_metadata(self, video_path: Path) -> VideoProbeMetadata`
  No docstring; inspect the linked implementation.

- [VideoProbe._positive_float, line 112](../../backend/src/castle_qa/services/video_probe.py#L112): `_positive_float(value: object) -> float &#124; None`
  No docstring; inspect the linked implementation.

- [VideoProbe._get_packet_duration, line 120](../../backend/src/castle_qa/services/video_probe.py#L120): `_get_packet_duration(cls, video_path: Path) -> float`
  No docstring; inspect the linked implementation.

- [VideoProbe._positive_or_zero_float, line 157](../../backend/src/castle_qa/services/video_probe.py#L157): `_positive_or_zero_float(value: object) -> float &#124; None`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/video_qa_service.py

- [GroundedVideoQAService.__init__, line 21](../../backend/src/castle_qa/services/video_qa_service.py#L21): `__init__(self, prompt_path: Path=Path('prompts/video_qa.txt'), llm_generator: Callable[[str], str] &#124; None=None)`
  No docstring; inspect the linked implementation.

- [GroundedVideoQAService.answer_question, line 38](../../backend/src/castle_qa/services/video_qa_service.py#L38): `answer_question(self, question: str, analysis: VideoAnalysis &#124; None=None, *, video_id: str &#124; None=None, analysis_id: str &#124; None=None) -> VideoQAAnswer`
  Answer a question with grounded evidence.

- [GroundedVideoQAService._answer_with_llm, line 85](../../backend/src/castle_qa/services/video_qa_service.py#L85): `_answer_with_llm(self, question: str, analysis: VideoAnalysis, video_id: str &#124; None, analysis_id: str &#124; None) -> VideoQAAnswer`
  No docstring; inspect the linked implementation.

- [GroundedVideoQAService._answer_from_analysis, line 162](../../backend/src/castle_qa/services/video_qa_service.py#L162): `_answer_from_analysis(self, question: str, analysis: VideoAnalysis, video_id: str &#124; None, analysis_id: str &#124; None) -> VideoQAAnswer`
  No docstring; inspect the linked implementation.

- [GroundedVideoQAService._parse_json_response, line 267](../../backend/src/castle_qa/services/video_qa_service.py#L267): `_parse_json_response(raw: str) -> dict`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/video_service.py

- [VideoItem.to_dict, line 54](../../backend/src/castle_qa/services/video_service.py#L54): `to_dict(self) -> dict`
  No docstring; inspect the linked implementation.

- [VideoItem.to_safe_dict, line 59](../../backend/src/castle_qa/services/video_service.py#L59): `to_safe_dict(self) -> dict`
  Return dict without exposing internal server filesystem path.

- [VideoService.__init__, line 71](../../backend/src/castle_qa/services/video_service.py#L71): `__init__(self, base_dir: Path &#124; None=None, probe: VideoProbe &#124; None=None, clip_extractor: VideoClipExtractor &#124; None=None, max_upload_size: int=DEFAULT_MAX_UPLOAD_SIZE, temporary_clip_dir: Path &#124; None=None, session_service: TemporarySessionService &#124; None=None, stream_tracker: StreamLeaseTracker &#124; None=None, max_concurrent_uploads: int=DEFAULT_MAX_CONCURRENT_UPLOADS, max_aggregate_temporary_storage: int=DEFAULT_MAX_AGGREGATE_TEMP_BYTES, max_clip_upload_size: int=DEFAULT_MAX_CLIP_UPLOAD_SIZE, max_clip_duration_seconds: float=DEFAULT_MAX_CLIP_DURATION)`
  No docstring; inspect the linked implementation.

- [VideoService.session_service, line 145](../../backend/src/castle_qa/services/video_service.py#L145): `session_service(self) -> TemporarySessionService`
  No docstring; inspect the linked implementation.

- [VideoService.stream_tracker, line 149](../../backend/src/castle_qa/services/video_service.py#L149): `stream_tracker(self) -> StreamLeaseTracker`
  No docstring; inspect the linked implementation.

- [VideoService.get_aggregate_temporary_size, line 152](../../backend/src/castle_qa/services/video_service.py#L152): `get_aggregate_temporary_size(self) -> int`
  Calculate total byte size of all stored temporary clips and in-flight temporary files.

- [VideoService._reserve_upload_quota, line 173](../../backend/src/castle_qa/services/video_service.py#L173): `_reserve_upload_quota(self, requested_bytes: int) -> Path`
  Atomically reserve storage quota and a concurrent upload slot across all worker processes. Raises ValueError if concurrent capacity is reached or aggregate quota would be exceeded. Returns the Path of the reservation file.

- [VideoService._check_disk_space, line 248](../../backend/src/castle_qa/services/video_service.py#L248): `_check_disk_space(self, target_dir: Path, required_bytes: int) -> None`
  Ensure server has sufficient disk space before accepting uploads.

- [VideoService.save_upload, line 258](../../backend/src/castle_qa/services/video_service.py#L258): `save_upload(self, file_obj: BinaryIO, original_filename: str, content_type: str &#124; None=None) -> VideoItem`
  Safely stream and validate an uploaded video file (standard/backward-compatible endpoint).

- [VideoService.save_temporary_clip, line 334](../../backend/src/castle_qa/services/video_service.py#L334): `save_temporary_clip(self, file_obj: BinaryIO, original_filename: str, content_type: str &#124; None=None, session_id: str &#124; None=None, session_token: str &#124; None=None, source_metadata: dict &#124; None=None, max_upload_size: int &#124; None=None, max_duration_seconds: float &#124; None=None, retention_hours: int=DEFAULT_RETENTION_HOURS) -> VideoItem`
  Safely stream, validate, and store a temporary short video clip for Qwen inference. Enforces size limit during streaming, concurrency limit, aggregate quota, and duration limit with FFprobe. Does NOT write to permanent CASTLE dataset directories.

- [VideoService.clean_expired_clips, line 507](../../backend/src/castle_qa/services/video_service.py#L507): `clean_expired_clips(self, job_repository: Any=None) -> list[str]`
  Safely purge temporary clips that have passed their 24h retention period, UNLESS an active (queued/running) job or active video stream requires them. Existing CASTLE datasets and permanent videos are NEVER touched.

- [VideoService._video_lifecycle_guard, line 526](../../backend/src/castle_qa/services/video_service.py#L526): `_video_lifecycle_guard(self, video_id: str)`
  Coordinate stream acquisition and media deletion across processes.

- [VideoService.video_lifecycle_guard, line 546](../../backend/src/castle_qa/services/video_service.py#L546): `video_lifecycle_guard(self, video_id: str)`
  Public coordination guard for endpoints that create media-dependent jobs.

- [VideoService.acquire_video_stream, line 550](../../backend/src/castle_qa/services/video_service.py#L550): `acquire_video_stream(self, video_id: str) -> tuple[VideoItem, str]`
  Acquire a stream lease atomically with respect to temporary media cleanup.

- [VideoService.get_temporary_clip_metadata, line 558](../../backend/src/castle_qa/services/video_service.py#L558): `get_temporary_clip_metadata(self, video_id: str) -> VideoItem &#124; None`
  Read a temporary clip's retained provenance metadata, even after media deletion.

- [VideoService.delete_temporary_clip, line 593](../../backend/src/castle_qa/services/video_service.py#L593): `delete_temporary_clip(self, video_id: str, *, job_repository: Any=None) -> bool`
  Delete only a temporary clip's media after jobs and streams release it. The metadata file is retained as a tombstone so saved analyses keep their source timing, session authorization, and video-availability state.

- [VideoService.is_temporary_clip_delete_pending, line 627](../../backend/src/castle_qa/services/video_service.py#L627): `is_temporary_clip_delete_pending(self, video_id: str) -> bool`
  No docstring; inspect the linked implementation.

- [VideoService._set_temporary_clip_delete_pending, line 637](../../backend/src/castle_qa/services/video_service.py#L637): `_set_temporary_clip_delete_pending(self, video_id: str, pending: bool) -> None`
  No docstring; inspect the linked implementation.

- [VideoService.list_videos, line 650](../../backend/src/castle_qa/services/video_service.py#L650): `list_videos(self, session_id: str &#124; None=None) -> list[VideoItem]`
  List all videos in storage directories. Privacy protection: Temporary clips are NEVER returned in the global list (session_id=None). Only permanent videos and (if session_id is provided) temporary clips belonging to that session are returned.

- [VideoService.get_video, line 687](../../backend/src/castle_qa/services/video_service.py#L687): `get_video(self, video_id_or_name: str, session_id: str &#124; None=None, session_token: str &#124; None=None) -> VideoItem &#124; None`
  Retrieve a video by video_id, exact filename, or path stem. For temporary clips, verifies session ownership if session_token is provided.

- [VideoService.extract_clip, line 748](../../backend/src/castle_qa/services/video_service.py#L748): `extract_clip(self, video_id: str, timestamp_str: str, before_seconds: float=15.0, after_seconds: float=15.0) -> ClipResult`
  Extract a temporal subclip around the specified timestamp.

- [VideoService._save_metadata, line 773](../../backend/src/castle_qa/services/video_service.py#L773): `_save_metadata(self, item: VideoItem) -> None`
  No docstring; inspect the linked implementation.

- [VideoService._load_or_probe_metadata, line 778](../../backend/src/castle_qa/services/video_service.py#L778): `_load_or_probe_metadata(self, file_path: Path) -> VideoItem`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/video_understanding/factory.py

- [VideoUnderstandingFactory.create, line 9](../../backend/src/castle_qa/services/video_understanding/factory.py#L9): `create(settings: Settings) -> VideoUnderstandingService`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/video_understanding/local_qwen_video_understanding_service.py

- [LocalQwenVideoUnderstandingService.__init__, line 14](../../backend/src/castle_qa/services/video_understanding/local_qwen_video_understanding_service.py#L14): `__init__(self, model_name: str, fps: float, max_new_tokens: int, prompt_path: Path, max_video_frames: int=64)`
  No docstring; inspect the linked implementation.

- [LocalQwenVideoUnderstandingService.generate_text, line 84](../../backend/src/castle_qa/services/video_understanding/local_qwen_video_understanding_service.py#L84): `generate_text(self, prompt: str, max_new_tokens: int=768) -> str`
  Run text-only generation with the already loaded local Qwen model.

- [LocalQwenVideoUnderstandingService.analyze, line 117](../../backend/src/castle_qa/services/video_understanding/local_qwen_video_understanding_service.py#L117): `analyze(self, clip: ClipResult) -> VideoAnalysis`
  No docstring; inspect the linked implementation.

- [LocalQwenVideoUnderstandingService._parse_json, line 224](../../backend/src/castle_qa/services/video_understanding/local_qwen_video_understanding_service.py#L224): `_parse_json(response: str) -> dict`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/video_understanding/mock_video_understanding_service.py

- [MockVideoUnderstandingService.analyze, line 10](../../backend/src/castle_qa/services/video_understanding/mock_video_understanding_service.py#L10): `analyze(self, clip: ClipResult) -> VideoAnalysis`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/services/video_understanding/video_understanding_service.py

- [VideoUnderstandingService.analyze, line 8](../../backend/src/castle_qa/services/video_understanding/video_understanding_service.py#L8): `analyze(self, clip: ClipResult) -> VideoAnalysis`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/utils/timestamp.py

- [Timestamp.__init__, line 3](../../backend/src/castle_qa/utils/timestamp.py#L3): `__init__(self, value: str)`
  No docstring; inspect the linked implementation.

- [Timestamp._parse, line 8](../../backend/src/castle_qa/utils/timestamp.py#L8): `_parse(value: str) -> float`
  No docstring; inspect the linked implementation.

- [Timestamp.from_seconds, line 33](../../backend/src/castle_qa/utils/timestamp.py#L33): `from_seconds(cls, seconds: float) -> 'Timestamp'`
  No docstring; inspect the linked implementation.

- [Timestamp.seconds, line 54](../../backend/src/castle_qa/utils/timestamp.py#L54): `seconds(self) -> float`
  No docstring; inspect the linked implementation.

- [Timestamp.value, line 58](../../backend/src/castle_qa/utils/timestamp.py#L58): `value(self) -> str`
  No docstring; inspect the linked implementation.

- [Timestamp.__str__, line 61](../../backend/src/castle_qa/utils/timestamp.py#L61): `__str__(self) -> str`
  No docstring; inspect the linked implementation.

### backend/src/castle_qa/workers/entrypoint.py

- [configure_logging, line 50](../../backend/src/castle_qa/workers/entrypoint.py#L50): `configure_logging() -> None`
  Configure worker process logging.

- [run_until_stopped, line 63](../../backend/src/castle_qa/workers/entrypoint.py#L63): `run_until_stopped(runner: WorkerRunner) -> None`
  Run the worker until SIGINT or SIGTERM is received. Restore previous signal handlers on exit.

- [run_until_stopped.<locals>.handle_shutdown, line 70](../../backend/src/castle_qa/workers/entrypoint.py#L70): `handle_shutdown(signum, frame)`
  No docstring; inspect the linked implementation.

- [run_demo, line 84](../../backend/src/castle_qa/workers/entrypoint.py#L84): `run_demo(poll_interval_seconds: float, once: bool) -> None`
  Run a mock worker with an isolated temporary database. No real CASTLE jobs or question results are modified.

- [create_job_handler, line 152](../../backend/src/castle_qa/workers/entrypoint.py#L152): `create_job_handler(analysis_repo: VideoAnalysisRepository, question_repo: QuestionRepository, mock_models: bool=False, inference_mode: str &#124; None=None) -> Callable[[InferenceJob], str]`
  Factory creating a multi-task job execution handler. Strictly distinguishes between 'real' and 'mock' inference modes. Never silently falls back to mock if real mode is explicitly configured.

- [create_job_handler.<locals>.handle_job, line 246](../../backend/src/castle_qa/workers/entrypoint.py#L246): `handle_job(job: InferenceJob) -> str`
  No docstring; inspect the linked implementation.

- [run_worker, line 286](../../backend/src/castle_qa/workers/entrypoint.py#L286): `run_worker(poll_interval_seconds: float, mock_models: bool, once: bool, worker_id: str &#124; None=None, database_path: Path &#124; None=None, inference_mode: str &#124; None=None) -> None`
  Run worker against the live job database.

- [run_worker.<locals>.cleanup_terminal_video_job, line 319](../../backend/src/castle_qa/workers/entrypoint.py#L319): `cleanup_terminal_video_job(job: InferenceJob) -> None`
  No docstring; inspect the linked implementation.

- [main, line 361](../../backend/src/castle_qa/workers/entrypoint.py#L361): `main() -> int`
  Parse command-line options and start the worker.

### backend/src/castle_qa/workers/job_worker.py

- [InferenceJobWorker.__init__, line 26](../../backend/src/castle_qa/workers/job_worker.py#L26): `__init__(self, repository: JobRepository, generate_and_save: Callable[[InferenceJob], str], worker_id: str &#124; None=None, heartbeat_interval_seconds: float=5.0, on_terminal: Callable[[InferenceJob], None] &#124; None=None)`
  No docstring; inspect the linked implementation.

- [InferenceJobWorker.finalize_terminal, line 40](../../backend/src/castle_qa/workers/job_worker.py#L40): `finalize_terminal(self, job: InferenceJob) -> None`
  No docstring; inspect the linked implementation.

- [InferenceJobWorker.worker_id, line 49](../../backend/src/castle_qa/workers/job_worker.py#L49): `worker_id(self) -> str`
  No docstring; inspect the linked implementation.

- [InferenceJobWorker.process_next, line 52](../../backend/src/castle_qa/workers/job_worker.py#L52): `process_next(self) -> InferenceJob &#124; None`
  No docstring; inspect the linked implementation.

- [InferenceJobWorker.process_next.<locals>.send_heartbeats, line 68](../../backend/src/castle_qa/workers/job_worker.py#L68): `send_heartbeats() -> None`
  No docstring; inspect the linked implementation.

- [InferenceJobWorker._get_updated_job, line 186](../../backend/src/castle_qa/workers/job_worker.py#L186): `_get_updated_job(self, job_id: str) -> InferenceJob`
  Retrieve the updated job after processing.

### backend/src/castle_qa/workers/worker_runner.py

- [JobProcessor.process_next, line 19](../../backend/src/castle_qa/workers/worker_runner.py#L19): `process_next(self) -> InferenceJob &#124; None`
  No docstring; inspect the linked implementation.

- [WorkerRunner.__init__, line 30](../../backend/src/castle_qa/workers/worker_runner.py#L30): `__init__(self, worker: JobProcessor, poll_interval_seconds: float=2.0, repository: Any &#124; None=None, stale_check_interval_seconds: float=30.0)`
  No docstring; inspect the linked implementation.

- [WorkerRunner.request_stop, line 61](../../backend/src/castle_qa/workers/worker_runner.py#L61): `request_stop(self) -> None`
  Request a graceful shutdown. If a job is currently processing, allow it to finish first.

- [WorkerRunner.run_forever, line 75](../../backend/src/castle_qa/workers/worker_runner.py#L75): `run_forever(self) -> None`
  Poll the job queue until shutdown is requested.

## Frontend source exports

A lexical index of top-level exported declarations. Interfaces/types describe compile-time contracts; exported functions/components can execute.

### frontend/src/App.tsx

- [Line 29](../../frontend/src/App.tsx#L29): `export const App: React.FC = () => {`

### frontend/src/features/annotations/AnnotationReviewWorkspace.tsx

- [Line 57](../../frontend/src/features/annotations/AnnotationReviewWorkspace.tsx#L57): `export const AnnotationReviewWorkspace: React.FC<AnnotationReviewWorkspaceProps> = ({`

### frontend/src/features/annotations/WhodunnitExportModal.tsx

- [Line 11](../../frontend/src/features/annotations/WhodunnitExportModal.tsx#L11): `export const WhodunnitExportModal: React.FC<WhodunnitExportModalProps> = ({`

### frontend/src/features/question-answering/GroundedQAPanel.tsx

- [Line 27](../../frontend/src/features/question-answering/GroundedQAPanel.tsx#L27): `export const GroundedQAPanel: React.FC<GroundedQAPanelProps> = ({`

### frontend/src/features/question-generation/criteriaFiles.ts

- [Line 1](../../frontend/src/features/question-generation/criteriaFiles.ts#L1): `export const MAX_CRITERIA_FILE_BYTES = 16 * 1024;`
- [Line 2](../../frontend/src/features/question-generation/criteriaFiles.ts#L2): `export const MAX_CRITERIA_CHARACTERS = 16_384;`
- [Line 6](../../frontend/src/features/question-generation/criteriaFiles.ts#L6): `export function criteriaFileExtension(fileName: string): string {`
- [Line 26](../../frontend/src/features/question-generation/criteriaFiles.ts#L26): `export async function readCriteriaFile(file: File): Promise<string> {`

### frontend/src/features/question-generation/QuestionGenerationWorkspace.tsx

- [Line 16](../../frontend/src/features/question-generation/QuestionGenerationWorkspace.tsx#L16): `export const QuestionGenerationWorkspace: React.FC<QuestionGenerationWorkspaceProps> = ({`

### frontend/src/features/video-understanding/TimelineView.tsx

- [Line 28](../../frontend/src/features/video-understanding/TimelineView.tsx#L28): `export const TimelineView: React.FC<TimelineViewProps> = ({`

### frontend/src/features/videos/analysisWindows.ts

- [Line 1](../../frontend/src/features/videos/analysisWindows.ts#L1): `export interface AnalysisWindow {`
- [Line 7](../../frontend/src/features/videos/analysisWindows.ts#L7): `export const MAX_SOURCE_INTERVAL_SECONDS = 10 * 60;`
- [Line 8](../../frontend/src/features/videos/analysisWindows.ts#L8): `export const ANALYSIS_WINDOW_SECONDS = 90;`
- [Line 9](../../frontend/src/features/videos/analysisWindows.ts#L9): `export const ANALYSIS_WINDOW_OVERLAP_SECONDS = 10;`
- [Line 10](../../frontend/src/features/videos/analysisWindows.ts#L10): `export const MAX_UPLOADED_CLIP_SECONDS = MAX_SOURCE_INTERVAL_SECONDS;`
- [Line 11](../../frontend/src/features/videos/analysisWindows.ts#L11): `export const MAX_UPLOADED_CLIP_BYTES = 1024 * 1024 * 1024;`
- [Line 13](../../frontend/src/features/videos/analysisWindows.ts#L13): `export function createAnalysisWindows(`
- [Line 40](../../frontend/src/features/videos/analysisWindows.ts#L40): `export function formatWindowOutputName(sourceFilename: string, window: AnalysisWindow): string {`
- [Line 52](../../frontend/src/features/videos/analysisWindows.ts#L52): `export function getRetryableWindowIds(`

### frontend/src/features/videos/browserCaptureExtractor.ts

- [Line 10](../../frontend/src/features/videos/browserCaptureExtractor.ts#L10): `export interface BrowserCaptureProgress {`
- [Line 18](../../frontend/src/features/videos/browserCaptureExtractor.ts#L18): `export interface BrowserCaptureResult {`
- [Line 33](../../frontend/src/features/videos/browserCaptureExtractor.ts#L33): `export interface ValidatedVideoMetadata {`
- [Line 41](../../frontend/src/features/videos/browserCaptureExtractor.ts#L41): `export async function validateVideoFile(file: File, timeoutMs = 10000): Promise<ValidatedVideoMetadata> {`
- [Line 104](../../frontend/src/features/videos/browserCaptureExtractor.ts#L104): `export function isBrowserCaptureSupported(): boolean {`
- [Line 114](../../frontend/src/features/videos/browserCaptureExtractor.ts#L114): `export function getPreferredMimeType(): string {`
- [Line 144](../../frontend/src/features/videos/browserCaptureExtractor.ts#L144): `export async function measureVideoFileDuration(file: File): Promise<number> {`
- [Line 206](../../frontend/src/features/videos/browserCaptureExtractor.ts#L206): `export async function extractClipWithBrowserCapture(`

### frontend/src/features/videos/ClipExtractionModal.tsx

- [Line 44](../../frontend/src/features/videos/ClipExtractionModal.tsx#L44): `export interface ClipExtractionModalProps {`
- [Line 52](../../frontend/src/features/videos/ClipExtractionModal.tsx#L52): `export const ClipExtractionModal: React.FC<ClipExtractionModalProps> = ({`

### frontend/src/features/videos/ClipSelectionPanel.tsx

- [Line 26](../../frontend/src/features/videos/ClipSelectionPanel.tsx#L26): `export interface ClipSelectionPanelProps {`
- [Line 41](../../frontend/src/features/videos/ClipSelectionPanel.tsx#L41): `export const ClipSelectionPanel: React.FC<ClipSelectionPanelProps> = ({`

### frontend/src/features/videos/nativeCommandGenerator.ts

- [Line 14](../../frontend/src/features/videos/nativeCommandGenerator.ts#L14): `export type SupportedShell = 'powershell' &#124; 'cmd' &#124; 'bash';`
- [Line 15](../../frontend/src/features/videos/nativeCommandGenerator.ts#L15): `export type NativeExtractionMode = 'frame_accurate' &#124; 'fast_copy';`
- [Line 17](../../frontend/src/features/videos/nativeCommandGenerator.ts#L17): `export interface NativeCommandOptions {`
- [Line 26](../../frontend/src/features/videos/nativeCommandGenerator.ts#L26): `export interface GeneratedNativeCommand {`
- [Line 38](../../frontend/src/features/videos/nativeCommandGenerator.ts#L38): `export interface GeneratedNativeBatchCommand {`
- [Line 47](../../frontend/src/features/videos/nativeCommandGenerator.ts#L47): `export function stripControlChars(val: string): string {`
- [Line 54](../../frontend/src/features/videos/nativeCommandGenerator.ts#L54): `export function ensureSafeCliPath(pathStr: string, isWindows: boolean = false): string {`
- [Line 68](../../frontend/src/features/videos/nativeCommandGenerator.ts#L68): `export function sanitizeFilename(name: string, defaultExt = 'mp4'): string {`
- [Line 86](../../frontend/src/features/videos/nativeCommandGenerator.ts#L86): `export function formatTimestampForFile(seconds: number): string {`
- [Line 97](../../frontend/src/features/videos/nativeCommandGenerator.ts#L97): `export function escapePowerShellArg(arg: string): string {`
- [Line 108](../../frontend/src/features/videos/nativeCommandGenerator.ts#L108): `export function escapeCmdArg(arg: string, forScript: boolean = false): string {`
- [Line 121](../../frontend/src/features/videos/nativeCommandGenerator.ts#L121): `export function escapeBashArg(arg: string): string {`
- [Line 130](../../frontend/src/features/videos/nativeCommandGenerator.ts#L130): `export function generateNativeCommand(`
- [Line 265](../../frontend/src/features/videos/nativeCommandGenerator.ts#L265): `export function generateNativeBatchCommand(`

### frontend/src/features/videos/StagedClipCard.tsx

- [Line 18](../../frontend/src/features/videos/StagedClipCard.tsx#L18): `export interface StagedClipCardProps {`
- [Line 33](../../frontend/src/features/videos/StagedClipCard.tsx#L33): `export const StagedClipCard: React.FC<StagedClipCardProps> = ({`

### frontend/src/features/videos/timestampUtils.ts

- [Line 15](../../frontend/src/features/videos/timestampUtils.ts#L15): `export function formatTimestamp(seconds: number): string {`
- [Line 43](../../frontend/src/features/videos/timestampUtils.ts#L43): `export function parseTimestamp(input: string): number &#124; null {`
- [Line 87](../../frontend/src/features/videos/timestampUtils.ts#L87): `export interface IntervalValidationResult {`
- [Line 95](../../frontend/src/features/videos/timestampUtils.ts#L95): `export function validateInterval(`
- [Line 146](../../frontend/src/features/videos/timestampUtils.ts#L146): `export function formatDuration(seconds: number): string {`
- [Line 170](../../frontend/src/features/videos/timestampUtils.ts#L170): `export function generateSelectionId(): string {`

### frontend/src/features/videos/useLocalVideo.ts

- [Line 4](../../frontend/src/features/videos/useLocalVideo.ts#L4): `export interface UseLocalVideoResult {`
- [Line 25](../../frontend/src/features/videos/useLocalVideo.ts#L25): `export function isSupportedVideoFile(file: File): boolean {`
- [Line 36](../../frontend/src/features/videos/useLocalVideo.ts#L36): `export function generateSourceInstanceId(): string {`
- [Line 43](../../frontend/src/features/videos/useLocalVideo.ts#L43): `export function useLocalVideo(onVideoSelected?: (video: LocalVideoItem) => void): UseLocalVideoResult {`

### frontend/src/features/videos/VideoPlayer.tsx

- [Line 19](../../frontend/src/features/videos/VideoPlayer.tsx#L19): `export interface VideoSeekRequest {`
- [Line 25](../../frontend/src/features/videos/VideoPlayer.tsx#L25): `export interface VideoPlayerProps {`
- [Line 38](../../frontend/src/features/videos/VideoPlayer.tsx#L38): `export const VideoPlayer: React.FC<VideoPlayerProps> = ({`

### frontend/src/features/videos/VideoUploadModal.tsx

- [Line 12](../../frontend/src/features/videos/VideoUploadModal.tsx#L12): `export const VideoUploadModal: React.FC<VideoUploadModalProps> = ({`

### frontend/src/features/videos/WindowedClipBatchCard.tsx

- [Line 6](../../frontend/src/features/videos/WindowedClipBatchCard.tsx#L6): `export type WindowTaskStatus = 'ready' &#124; 'uploading' &#124; 'processing' &#124; 'completed' &#124; 'failed';`
- [Line 7](../../frontend/src/features/videos/WindowedClipBatchCard.tsx#L7): `export interface WindowTaskState { status: WindowTaskStatus; analysisId?: string; error?: string; }`
- [Line 20](../../frontend/src/features/videos/WindowedClipBatchCard.tsx#L20): `export const WindowedClipBatchCard: React.FC<Props> = ({ clips, states, isAnalyzing, progressText, batchError, onAnalyze, onCancel, onClear }) => {`

### frontend/src/features/videos/WindowedClipPreparationModal.tsx

- [Line 24](../../frontend/src/features/videos/WindowedClipPreparationModal.tsx#L24): `export const WindowedClipPreparationModal: React.FC<Props> = ({ isOpen, localVideo, interval, onClose, onClipsPrepared }) => {`

### frontend/src/shared/api/client.ts

- [Line 42](../../frontend/src/shared/api/client.ts#L42): `export const api = {`

### frontend/src/shared/components/Header.tsx

- [Line 4](../../frontend/src/shared/components/Header.tsx#L4): `export const Header: React.FC = () => {`

### frontend/src/shared/types/index.ts

- [Line 1](../../frontend/src/shared/types/index.ts#L1): `export type JobStatus = 'queued' &#124; 'running' &#124; 'completed' &#124; 'failed';`
- [Line 3](../../frontend/src/shared/types/index.ts#L3): `export type ReviewStatus = 'pending' &#124; 'accepted' &#124; 'rejected' &#124; 'edited';`
- [Line 5](../../frontend/src/shared/types/index.ts#L5): `export type SessionStatus = 'in_progress' &#124; 'approved' &#124; 'rejected';`
- [Line 7](../../frontend/src/shared/types/index.ts#L7): `export interface VideoItem {`
- [Line 23](../../frontend/src/shared/types/index.ts#L23): `export interface VideoIntervalSelection {`
- [Line 33](../../frontend/src/shared/types/index.ts#L33): `export type ExtractionMethod =`
- [Line 38](../../frontend/src/shared/types/index.ts#L38): `export type TemporalAlignmentStatus =`
- [Line 44](../../frontend/src/shared/types/index.ts#L44): `export interface StagedClipItem {`
- [Line 69](../../frontend/src/shared/types/index.ts#L69): `export interface LocalVideoItem {`
- [Line 81](../../frontend/src/shared/types/index.ts#L81): `export interface ServerVideoItem extends VideoItem {`
- [Line 85](../../frontend/src/shared/types/index.ts#L85): `export type ActiveVideoSource = LocalVideoItem &#124; ServerVideoItem;`
- [Line 87](../../frontend/src/shared/types/index.ts#L87): `export function isLocalVideo(video: ActiveVideoSource &#124; null &#124; undefined): video is LocalVideoItem {`
- [Line 91](../../frontend/src/shared/types/index.ts#L91): `export function formatFileSize(bytes: number): string {`
- [Line 100](../../frontend/src/shared/types/index.ts#L100): `export interface InferenceJob {`
- [Line 113](../../frontend/src/shared/types/index.ts#L113): `export interface GeneratedQuestion {`
- [Line 127](../../frontend/src/shared/types/index.ts#L127): `export interface QuestionGenerationResponse {`
- [Line 136](../../frontend/src/shared/types/index.ts#L136): `export interface ObservableEvent {`
- [Line 154](../../frontend/src/shared/types/index.ts#L154): `export interface VideoAnalysis {`
- [Line 179](../../frontend/src/shared/types/index.ts#L179): `export interface VideoQAAnswer {`
- [Line 198](../../frontend/src/shared/types/index.ts#L198): `export interface EventReviewItem {`
- [Line 218](../../frontend/src/shared/types/index.ts#L218): `export interface QuestionReviewItem {`
- [Line 232](../../frontend/src/shared/types/index.ts#L232): `export interface AnnotationReviewSession {`

