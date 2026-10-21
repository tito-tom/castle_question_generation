import {
  AnnotationReviewSession,
  InferenceJob,
  VideoAnalysis,
  VideoItem,
  VideoQAAnswer,
} from '../types/index';

const API_BASE = '/api/v1';

let activeSessionId: string | null = null;
let activeSessionToken: string | null = null;

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (activeSessionId) {
    headers['X-Session-ID'] = activeSessionId;
  }
  if (activeSessionToken) {
    headers['X-Session-Token'] = activeSessionToken;
  }
  return headers;
}

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
  // Session credentials management
  setSessionCredentials(sessionId?: string | null, sessionToken?: string | null): void {
    if (sessionId !== undefined) activeSessionId = sessionId;
    if (sessionToken !== undefined) activeSessionToken = sessionToken;
  },

  getSessionCredentials(): { sessionId: string | null; sessionToken: string | null } {
    return { sessionId: activeSessionId, sessionToken: activeSessionToken };
  },

  clearSessionCredentials(): void {
    activeSessionId = null;
    activeSessionToken = null;
  },

  // Videos
  async getVideos(): Promise<{ videos: VideoItem[] }> {
    const res = await fetch(`${API_BASE}/videos`, {
      headers: getAuthHeaders(),
    });
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

  async uploadTemporaryClip(
    clipFile: File,
    metadata?: {
      sessionId?: string;
      sessionToken?: string;
      sourceFilename?: string;
      sourceVideoRef?: string;
      sourceStartSeconds?: number;
      sourceEndSeconds?: number;
      sourceDurationSeconds?: number;
      extractionMethod?: string;
      alignmentStatus?: string;
      userConfirmed?: boolean;
    },
    onProgress?: (percent: number) => void
  ): Promise<VideoItem & { is_temporary?: boolean; session_id?: string; session_token?: string; expires_at?: string }> {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', clipFile);
      const effectiveSessionId = metadata?.sessionId || activeSessionId;
      const effectiveSessionToken = metadata?.sessionToken || activeSessionToken;

      if (effectiveSessionId) formData.append('session_id', effectiveSessionId);
      if (effectiveSessionToken) formData.append('session_token', effectiveSessionToken);
      if (metadata?.sourceFilename) formData.append('source_filename', metadata.sourceFilename);
      if (metadata?.sourceVideoRef) formData.append('source_video_ref', metadata.sourceVideoRef);
      if (metadata?.sourceStartSeconds !== undefined) formData.append('source_start_seconds', String(metadata.sourceStartSeconds));
      if (metadata?.sourceEndSeconds !== undefined) formData.append('source_end_seconds', String(metadata.sourceEndSeconds));
      if (metadata?.sourceDurationSeconds !== undefined) formData.append('source_duration_seconds', String(metadata.sourceDurationSeconds));
      if (metadata?.extractionMethod) formData.append('extraction_method', metadata.extractionMethod);
      if (metadata?.alignmentStatus) formData.append('alignment_status', metadata.alignmentStatus);
      if (metadata?.userConfirmed !== undefined) formData.append('user_confirmed', String(metadata.userConfirmed));

      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/videos/upload-clip`);

      if (effectiveSessionToken) {
        xhr.setRequestHeader('X-Session-Token', effectiveSessionToken);
      }
      if (effectiveSessionId) {
        xhr.setRequestHeader('X-Session-ID', effectiveSessionId);
      }

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            const tokenHdr = xhr.getResponseHeader('X-Session-Token');
            if (tokenHdr && !data.session_token) {
              data.session_token = tokenHdr;
            }
            if (data.session_id) activeSessionId = data.session_id;
            if (data.session_token) activeSessionToken = data.session_token;
            resolve(data);
          } catch {
            reject(new Error('Failed to parse upload response'));
          }
        } else {
          let errorDetail = `Upload failed with status ${xhr.status}`;
          try {
            const body = JSON.parse(xhr.responseText);
            if (body.detail) {
              errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
            }
          } catch {}
          reject(new Error(errorDetail));
        }
      };

      xhr.onerror = () => {
        reject(new Error('Network error during clip upload'));
      };

      xhr.send(formData);
    });
  },

  async touchSession(sessionId: string, sessionToken?: string): Promise<{ session_id: string; expires_at: string; last_active_at: string; state: string }> {
    const headers: Record<string, string> = { ...getAuthHeaders() };
    const effectiveToken = sessionToken || activeSessionToken;
    if (effectiveToken) headers['X-Session-Token'] = effectiveToken;
    const res = await fetch(`${API_BASE}/videos/session/${sessionId}/touch`, {
      method: 'POST',
      headers,
    });
    return handleResponse(res);
  },

  getVideoStreamUrl(videoId: string, start?: number, end?: number): string {
    let url = `${API_BASE}/videos/${videoId}/stream`;
    const params: string[] = [];
    if (start !== undefined && end !== undefined) {
      params.push(`start=${start}`, `end=${end}`);
    }
    if (activeSessionToken && videoId.startsWith('clip_')) {
      params.push(`token=${encodeURIComponent(activeSessionToken)}`);
    }
    if (params.length > 0) {
      url += `?${params.join('&')}`;
    }
    return url;
  },

  // Jobs
  async submitVideoUnderstanding(videoId: string, fps = 2.0): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/jobs/video-understandings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
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
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        analysis_id: analysisId,
        clip_duration_seconds: clipDurationSeconds,
        max_questions: maxQuestions,
      }),
    });
    return handleResponse(res);
  },

  async getJobStatus(jobId: string): Promise<InferenceJob> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      headers: getAuthHeaders(),
    });
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
    const res = await fetch(`${API_BASE}/analyses`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getAnalysis(analysisId: string): Promise<VideoAnalysis> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async saveAnalysisPersistent(analysisId: string): Promise<VideoAnalysis> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/save-persistent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
    });
    return handleResponse(res);
  },

  // Grounded Video QA
  async askVideoQuestion(videoId: string, question: string, analysisId?: string): Promise<VideoQAAnswer> {
    const res = await fetch(`${API_BASE}/qa/videos/${videoId}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ question, analysis_id: analysisId }),
    });
    return handleResponse(res);
  },

  async askAnalysisQuestion(analysisId: string, question: string): Promise<VideoQAAnswer> {
    const res = await fetch(`${API_BASE}/qa/analyses/${analysisId}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
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
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        analysis_id: analysisId,
        video_id: videoId,
        generation_id: generationId,
      }),
    });
    return handleResponse(res);
  },

  async getReviewSession(reviewId: string): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async updateEventReview(
    reviewId: string,
    eventIndex: number,
    payload: Record<string, unknown>
  ): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}/events/${eventIndex}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
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
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
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
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ overall_status: overallStatus, summary }),
    });
    return handleResponse(res);
  },

  async syncReviewSessionQuestions(
    reviewId: string,
    generationId: string
  ): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}/sync-questions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ generation_id: generationId }),
    });
    return handleResponse(res);
  },

  async saveQuestionGenerationPersistent(
    generationId: string
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/question-generations/${generationId}/save-persistent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
    });
    return handleResponse(res);
  },

  async saveReviewSessionPersistent(
    reviewId: string
  ): Promise<AnnotationReviewSession> {
    const res = await fetch(`${API_BASE}/annotations/sessions/${reviewId}/save-persistent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
    });
    return handleResponse(res);
  },

  getWhodunnitExportUrl(reviewId: string): string {
    let url = `${API_BASE}/annotations/sessions/${reviewId}/export/whodunnit`;
    if (activeSessionToken) {
      url += `?token=${encodeURIComponent(activeSessionToken)}`;
    }
    return url;
  },

  getWhodunnitCsvExportUrl(reviewId: string): string {
    let url = `${API_BASE}/annotations/sessions/${reviewId}/export/csv`;
    if (activeSessionToken) {
      url += `?token=${encodeURIComponent(activeSessionToken)}`;
    }
    return url;
  },
};
