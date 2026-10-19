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
  description: string;
  actor?: string | null;
  action?: string | null;
  object?: string | null;
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
}

export interface VideoQAAnswer {
  question: string;
  answer: string;
  confidence: number;
  is_observable: boolean;
  uncertainty_notes?: string | null;
  start_seconds?: number | null;
  end_seconds?: number | null;
  evidence_reasoning?: string | null;
  referenced_events: number[];
  video_id?: string | null;
  analysis_id?: string | null;
  clip_url?: string | null;
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
  events: EventReviewItem[];
  questions: QuestionReviewItem[];
}

