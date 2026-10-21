/**
 * CASTLE QA Studio - Timestamp Utilities
 *
 * High-precision timestamp formatting, parsing, and validation for local video interval selection.
 * Supports subsecond precision (milliseconds) and videos longer than 1 hour.
 */

/**
 * Format numeric seconds into HH:MM:SS.mmm format.
 * Examples:
 *   0 -> "00:00:00.000"
 *   75.5 -> "00:01:15.500"
 *   3675.123 -> "01:01:15.123"
 */
export function formatTimestamp(seconds: number): string {
  if (typeof seconds !== 'number' || isNaN(seconds) || !isFinite(seconds) || seconds < 0) {
    return '00:00:00.000';
  }

  const totalMs = Math.round(seconds * 1000);
  const hours = Math.floor(totalMs / 3600000);
  const minutes = Math.floor((totalMs % 3600000) / 60000);
  const secs = Math.floor((totalMs % 60000) / 1000);
  const ms = totalMs % 1000;

  const hStr = String(hours).padStart(2, '0');
  const mStr = String(minutes).padStart(2, '0');
  const sStr = String(secs).padStart(2, '0');
  const msStr = String(ms).padStart(3, '0');

  return `${hStr}:${mStr}:${sStr}.${msStr}`;
}

/**
 * Parse a timestamp string into numeric seconds with 3-decimal precision.
 * Supported formats:
 *   - "HH:MM:SS.mmm" or "H:MM:SS.mmm" or "HH:MM:SS" (e.g. "01:23:45.678", "1:05:00")
 *   - "MM:SS.mmm" or "M:SS.mmm" or "MM:SS" (e.g. "02:15.500", "5:30")
 *   - Plain seconds (e.g. "125.5", "60", "0.25")
 *
 * Returns null if the format is invalid or values are out of bounds (e.g. minutes >= 60).
 */
export function parseTimestamp(input: string): number | null {
  if (typeof input !== 'string') return null;
  const trimmed = input.trim();
  if (!trimmed || trimmed.startsWith('-')) return null;

  // Format 1: HH:MM:SS(.mmm)?
  const hmsRegex = /^(\d+):([0-5]?\d):([0-5]?\d)(?:\.(\d{1,3}))?$/;
  const hmsMatch = trimmed.match(hmsRegex);
  if (hmsMatch) {
    const hours = parseInt(hmsMatch[1], 10);
    const minutes = parseInt(hmsMatch[2], 10);
    const seconds = parseInt(hmsMatch[3], 10);
    const msStr = (hmsMatch[4] || '0').padEnd(3, '0').slice(0, 3);
    const ms = parseInt(msStr, 10);

    const totalSec = hours * 3600 + minutes * 60 + seconds + ms / 1000;
    return Math.round(totalSec * 1000) / 1000;
  }

  // Format 2: MM:SS(.mmm)?
  const msRegex = /^([0-5]?\d):([0-5]?\d)(?:\.(\d{1,3}))?$/;
  const msMatch = trimmed.match(msRegex);
  if (msMatch) {
    const minutes = parseInt(msMatch[1], 10);
    const seconds = parseInt(msMatch[2], 10);
    const msStr = (msMatch[3] || '0').padEnd(3, '0').slice(0, 3);
    const ms = parseInt(msStr, 10);

    const totalSec = minutes * 60 + seconds + ms / 1000;
    return Math.round(totalSec * 1000) / 1000;
  }

  // Format 3: Raw numeric seconds (e.g. "45.5" or "120")
  const rawRegex = /^\d+(?:\.\d{1,3})?$/;
  if (rawRegex.test(trimmed)) {
    const val = parseFloat(trimmed);
    if (!isNaN(val) && isFinite(val) && val >= 0) {
      return Math.round(val * 1000) / 1000;
    }
  }

  return null;
}

export interface IntervalValidationResult {
  isValid: boolean;
  error: string | null;
}

/**
 * Validates a video interval (start and end timestamps).
 */
export function validateInterval(
  start: number | null | undefined,
  end: number | null | undefined,
  videoDuration?: number | null,
  maxDuration?: number
): IntervalValidationResult {
  if (start === null || start === undefined || isNaN(start) || !isFinite(start)) {
    return { isValid: false, error: 'Start timestamp is required and must be a valid number.' };
  }

  if (end === null || end === undefined || isNaN(end) || !isFinite(end)) {
    return { isValid: false, error: 'End timestamp is required and must be a valid number.' };
  }

  if (start < 0) {
    return { isValid: false, error: 'Start timestamp cannot be negative.' };
  }

  if (end <= start) {
    return {
      isValid: false,
      error: 'End timestamp must be strictly greater than start timestamp.',
    };
  }

  if (videoDuration !== undefined && videoDuration !== null && videoDuration > 0) {
    // Give 0.05s buffer for floating point inaccuracies
    if (end > videoDuration + 0.05) {
      return {
        isValid: false,
        error: `End timestamp (${formatTimestamp(end)}) cannot exceed video duration (${formatTimestamp(videoDuration)}).`,
      };
    }
  }

  if (maxDuration !== undefined && maxDuration > 0) {
    const duration = end - start;
    if (duration > maxDuration) {
      return {
        isValid: false,
        error: `Interval duration (${duration.toFixed(1)}s) exceeds the maximum allowed duration of ${maxDuration}s.`,
      };
    }
  }

  return { isValid: true, error: null };
}

/**
 * Format a duration in seconds into a friendly string (e.g. "30.0s", "1m 15.2s", "1h 5m 20.0s").
 */
export function formatDuration(seconds: number): string {
  if (typeof seconds !== 'number' || isNaN(seconds) || !isFinite(seconds) || seconds <= 0) {
    return '0.0s';
  }

  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }

  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}m ${secs}s`;
  }

  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = (seconds % 60).toFixed(1);
  return `${hours}h ${mins}m ${secs}s`;
}

/**
 * Generate a client-side unique identifier for a video interval selection.
 */
export function generateSelectionId(): string {
  const timestamp = Date.now();
  const rand = Math.random().toString(36).substring(2, 8);
  return `sel_${timestamp}_${rand}`;
}

