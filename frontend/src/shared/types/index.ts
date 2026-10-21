export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export type ReviewStatus = 'pending' | 'accepted' | 'rejected' | 'edited';

export type SessionStatus = 'in_progress' | 'approved' | 'rejected';

export interface VideoItem {
  video_id: string;
  filename: string;
  duration_seconds: number;
  size_bytes: number;
  created_at?: string;
  width?: number;
  height?: number;
  fps?: number;
  codec_name?: string;
  is_temporary?: boolean;
  session_id?: string;
  session_token?: string;
  expires_at?: string;
}

export interface VideoIntervalSelection {
  id: string;
  videoRef: string;
  startSeconds: number;
  endSeconds: number;
  durationSeconds: number;
  label?: string;
  createdAt: string;
}

export type ExtractionMethod =
  | 'native_ffmpeg_assisted'
  | 'direct_import'
  | 'browser_capture';

export type TemporalAlignmentStatus =
  | 'verified'
  | 'user_confirmed'
  | 'approximate'
  | 'unverified';

export interface StagedClipItem {
  id: string;
  file: File;
  objectUrl: string;
  filename: string;
  sizeBytes: number;
  durationSeconds: number;
  measuredDurationSeconds?: number;
  width?: number;
  height?: number;
  method: ExtractionMethod;
  alignmentStatus: TemporalAlignmentStatus;
  userConfirmedAssociation: boolean;
  sourceVideoName: string;
  sourceVideoRef: string; // Collision-resistant sourceInstanceId
  sourceStartSeconds: number;
  sourceEndSeconds: number;
  sourceDurationSeconds: number;
  durationDeltaSeconds: number;
  notes?: string;
  createdAt: string;
}

export interface LocalVideoItem {
  sourceType: 'local';
  sourceInstanceId: string; // Unique collision-resistant client-side UUID
  file: File;
  objectUrl: string;
  filename: string;
  sizeBytes: number;
  durationSeconds?: number;
  width?: number;
  height?: number;
}

export interface ServerVideoItem extends VideoItem {
  sourceType: 'server';
}

export type ActiveVideoSource = LocalVideoItem | ServerVideoItem;

export function isLocalVideo(video: ActiveVideoSource | null | undefined): video is LocalVideoItem {
  return video !== null && video !== undefined && video.sourceType === 'local';
}

export function formatFileSize(bytes: number): string {
  if (bytes <= 0 || isNaN(bytes)) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = bytes / Math.pow(k, i);
  return `${val.toFixed(val >= 10 || i === 0 ? 0 : 1)} ${sizes[i]}`;
}

export interface InferenceJob {
  job_id: string;
  job_type: 'question_generation' | 'video_understanding';
  status: JobStatus;
  analysis_id?: string | null;
  video_id?: string | null;
  result_id?: string | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface ObservableEvent {
  start_seconds: number;
  end_seconds: number;
  clip_start_seconds?: number;
  clip_end_seconds?: number;
  source_start_seconds?: number | null;
  source_end_seconds?: number | null;
  time_offset_uncertainty?: number | null;
  description: string;
  actor?: string | null;
  action?: string | null;
  object?: string | null;
  object_name?: string | null;
  target?: string | null;
  confidence?: number | null;
}

export interface VideoAnalysis {
  analysis_id: string;
  clip_name: string;
  model_name: string;
  scene?: string | null;
  participants?: string[];
  objects?: string[];
  summary: string;
  events: ObservableEvent[];
  source_video_name?: string | null;
  source_start_seconds?: number | null;
  source_end_seconds?: number | null;
  temporal_alignment_status?: string | null;
  is_temporary?: boolean | null;
  is_persistent?: boolean | null;
  video_available?: boolean;
  is_mock?: boolean;
  inference_mode?: 'real' | 'mock' | 'legacy_unverified' | 'unknown';
  sampling_fps?: number | null;
  runtime_seconds?: number | null;
  device?: string | null;
  mock_notice?: string | null;
}

export interface VideoQAAnswer {
  question: string;
  answer: string;
  confidence: number;
  is_observable: boolean;
  confidence_type?: string;
  is_human_reviewed?: boolean;
  uncertainty_notes?: string | null;
  start_seconds?: number | null;
  end_seconds?: number | null;
  evidence_reasoning?: string | null;
  referenced_events: number[];
  video_id?: string | null;
  analysis_id?: string | null;
  clip_url?: string | null;
  is_mock?: boolean;
  mock_notice?: string | null;
}

export interface EventReviewItem {
  event_index: number;
  original_start_seconds: number;
  original_end_seconds: number;
  original_description: string;
  original_actor?: string | null;
  original_action?: string | null;
  original_object?: string | null;
  original_target?: string | null;
  status: ReviewStatus;
  reviewer_notes?: string | null;
  edited_start_seconds?: number | null;
  edited_end_seconds?: number | null;
  edited_description?: string | null;
  edited_actor?: string | null;
  edited_action?: string | null;
  edited_object?: string | null;
  edited_target?: string | null;
}

export interface QuestionReviewItem {
  question_index: number;
  original_question: string;
  original_answer?: string | null;
  actor_reference?: string | null;
  source_event_index?: number | null;
  evidence_start_seconds?: number | null;
  evidence_end_seconds?: number | null;
  status: ReviewStatus;
  reviewer_notes?: string | null;
  edited_question?: string | null;
  edited_answer?: string | null;
}

export interface AnnotationReviewSession {
  review_id: string;
  analysis_id: string;
  video_id?: string | null;
  generation_id?: string | null;
  created_at: string;
  updated_at: string;
  reviewer_id?: string | null;
  overall_status: SessionStatus;
  summary: string;
  is_persistent?: boolean | null;
  video_available?: boolean;
  is_mock?: boolean;
  inference_mode?: 'real' | 'mock' | 'legacy_unverified' | 'unknown';
  mock_notice?: string | null;
  events: EventReviewItem[];
  questions: QuestionReviewItem[];
}

