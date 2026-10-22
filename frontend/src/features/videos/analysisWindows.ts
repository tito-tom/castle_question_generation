export interface AnalysisWindow {
  index: number;
  startSeconds: number;
  endSeconds: number;
}

export const MAX_SOURCE_INTERVAL_SECONDS = 10 * 60;
export const ANALYSIS_WINDOW_SECONDS = 90;
export const ANALYSIS_WINDOW_OVERLAP_SECONDS = 10;
export const MAX_UPLOADED_CLIP_SECONDS = 120;
export const MAX_UPLOADED_CLIP_BYTES = 200 * 1024 * 1024;

export function createAnalysisWindows(
  startSeconds: number,
  endSeconds: number,
  windowSeconds = ANALYSIS_WINDOW_SECONDS,
  overlapSeconds = ANALYSIS_WINDOW_OVERLAP_SECONDS,
): AnalysisWindow[] {
  if (!Number.isFinite(startSeconds) || !Number.isFinite(endSeconds) || startSeconds < 0 || endSeconds <= startSeconds) {
    throw new Error('Select a valid interval with an end after the start.');
  }
  if (endSeconds - startSeconds > MAX_SOURCE_INTERVAL_SECONDS) {
    throw new Error('Selected intervals can be at most 10 minutes.');
  }
  if (!Number.isFinite(windowSeconds) || windowSeconds <= 0 || overlapSeconds < 0 || overlapSeconds >= windowSeconds) {
    throw new Error('Analysis window settings are invalid.');
  }

  const windows: AnalysisWindow[] = [];
  let cursor = startSeconds;
  while (cursor < endSeconds - 0.001) {
    const nextEnd = Math.min(cursor + windowSeconds, endSeconds);
    windows.push({ index: windows.length + 1, startSeconds: cursor, endSeconds: nextEnd });
    if (nextEnd >= endSeconds) break;
    cursor = nextEnd - overlapSeconds;
  }
  return windows;
}

export function formatWindowOutputName(sourceFilename: string, window: AnalysisWindow): string {
  const basename = sourceFilename.replace(/\.[^/.]+$/, '').replace(/[^\p{L}\p{N}_-]/gu, '_').slice(0, 70) || 'recording';
  const stamp = (seconds: number) => {
    const whole = Math.floor(seconds);
    const h = Math.floor(whole / 3600);
    const m = Math.floor((whole % 3600) / 60);
    const s = whole % 60;
    return `${String(h).padStart(2, '0')}-${String(m).padStart(2, '0')}-${String(s).padStart(2, '0')}`;
  };
  return `clip_${basename}_w${String(window.index).padStart(2, '0')}_${stamp(window.startSeconds)}_to_${stamp(window.endSeconds)}.mp4`;
}

export function getRetryableWindowIds(
  windows: Array<{ id: string }>,
  completedAnalysisIds: Record<string, string>,
): string[] {
  return windows.filter((window) => !completedAnalysisIds[window.id]).map((window) => window.id);
}
