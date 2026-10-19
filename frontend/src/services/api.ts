import {
  AnnotationReviewSession,
  InferenceJob,
  VideoAnalysis,
  VideoItem,
  VideoQAAnswer,
} from '../types';

const API_BASE = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body.detail) {
        errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Videos
  async getVideos(): Promise<{ videos: VideoItem[] }> {
    const res = await fetch(`${API_BASE}/videos`);
    return handleResponse(res);
  },

  async uploadVideo(file: File): Promise<VideoItem> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/videos/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  getVideoStreamUrl(videoId: string, start?: number, end?: number): string {
    let url = `${API_BASE}/videos/${videoId}/stream`;
    if (start !== undefined && end !== undefined) {
      url += `?start=${start}&end=${end}`;
    }
    return url;
  },

  // Jobs
  async submitVideoUnderstanding(videoId: string, fps = 2.0): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/jobs/video-understandings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, fps }),
    });
    return handleResponse(res);
  },

  async submitQuestionGeneration(
    analysisId: string,
    clipDurationSeconds: number,
    maxQuestions = 5
  ): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/jobs/question-generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_id: analysisId,
        clip_duration_seconds: clipDurationSeconds,
        max_questions: maxQuestions,
      }),
    });
    return handleResponse(res);
  },

  async getJobStatus(jobId: string): Promise<InferenceJob> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    return handleResponse(res);
  },

  async pollJobUntilFinished(
    jobId: string,
    intervalMs = 2000,
    onUpdate?: (job: InferenceJob) => void
  ): Promise<InferenceJob> {
    while (true) {
      const job = await this.getJobStatus(jobId);
      if (onUpdate) onUpdate(job);
      if (job.status === 'completed' || job.status === 'failed') {
        return job;
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  },

  // Analyses
  async getAnalyses(): Promise<{ analyses: Array<{ analysis_id: string; clip_name: string; model_name: string; event_count: number }> }> {
    const res = await fetch(`${API_BASE}/analyses`);
    return handleResponse(res);
  },

  async getAnalysis(analysisId: string): Promise<VideoAnalysis> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}`);
    return handleResponse(res);
  },

  // Grounded Video QA
  async askVideoQuestion(videoId: string, question: string, analysisId?: string): Promise<VideoQAAnswer> {
    const res = await fetch(`${API_BASE}/qa/videos/${videoId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, analysis_id: analysisId }),
    });
    return handleResponse(res);
  },

  async askAnalysisQuestion(analysisId: string, question: string): Promise<VideoQAAnswer> {
    const res = await fetch(`${API_BASE}/qa/analyses/${analysisId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    return handleResponse(res);
  },

  // Annotation Reviews & Whodunnit
  async createOrLoadReviewSession(
    analysisId: string,
    videoId?: string,
    generationId?: string
  ): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_id: analysisId,
        video_id: videoId,
        generation_id: generationId,
      }),
    });
    return handleResponse(res);
  },

  async getReviewSession(reviewId: string): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}`);
    return handleResponse(res);
  },

  async updateEventReview(
    reviewId: string,
    eventIndex: number,
    payload: Record<string, unknown>
  ): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}/events/${eventIndex}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateQuestionReview(
    reviewId: string,
    questionIndex: number,
    payload: Record<string, unknown>
  ): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}/questions/${questionIndex}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async updateSessionStatus(
    reviewId: string,
    overallStatus: string,
    summary?: string
  ): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ overall_status: overallStatus, summary }),
    });
    return handleResponse(res);
  },

  getWhodunnitExportUrl(reviewId: string): string {
    return `${API_BASE}/annotations/sessions/${reviewId}/export/whodunnit`;
  },

  getWhodunnitCsvExportUrl(reviewId: string): string {
    return `${API_BASE}/annotations/sessions/${reviewId}/export/csv`;
  },
};

