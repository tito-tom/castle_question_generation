/**
 * CASTLE QA Studio - Browser-Native Capture Extractor (Experimental Mode C)
 *
 * Uses HTMLMediaElement.captureStream() and MediaRecorder to capture short clips
 * directly inside the browser using the local File's blob object URL.
 *
 * Enforces resource cleanup, tab visibility monitoring, and duration delta inspection.
 */

export interface BrowserCaptureProgress {
  currentTime: number;
  startSeconds: number;
  endSeconds: number;
  percent: number;
  statusText: string;
}

export interface BrowserCaptureResult {
  file: File;
  objectUrl: string;
  filename: string;
  sizeBytes: number;
  actualDurationSeconds: number;
  requestedDurationSeconds: number;
  durationDeltaSeconds: number;
  mimeType: string;
  wasBackgroundThrottled: boolean;
  warningMessage?: string;
}

export function isBrowserCaptureSupported(): boolean {
  if (typeof window === 'undefined') return false;
  const hasMediaRecorder = typeof window.MediaRecorder !== 'undefined';
  const hasCaptureStream =
    typeof HTMLVideoElement !== 'undefined' &&
    (typeof (HTMLVideoElement.prototype as any).captureStream === 'function' ||
      typeof (HTMLVideoElement.prototype as any).mozCaptureStream === 'function');
  return hasMediaRecorder && hasCaptureStream;
}

export function getPreferredMimeType(): string {
  if (typeof window === 'undefined' || typeof window.MediaRecorder === 'undefined') {
    return 'video/webm';
  }

  const candidates = [
    'video/mp4;codecs=avc1,mp4a.40.2',
    'video/mp4;codecs=avc1',
    'video/mp4',
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
  ];

  for (const candidate of candidates) {
    try {
      if (MediaRecorder.isTypeSupported(candidate)) {
        return candidate;
      }
    } catch {
      // Continue searching
    }
  }

  return 'video/webm';
}

/**
 * Measure the actual decoded duration of a video File using an auxiliary element.
 */
export async function measureVideoFileDuration(file: File): Promise<number> {
  return new Promise((resolve) => {
    let resolved = false;
    let tempUrl = '';
    try {
      tempUrl = URL.createObjectURL(file);
    } catch {
      resolve(0);
      return;
    }

    const tempVideo = document.createElement('video');
    tempVideo.preload = 'metadata';

    const timer = setTimeout(() => {
      cleanup();
      if (!resolved) {
        resolved = true;
        resolve(0);
      }
    }, 4000);

    const cleanup = () => {
      clearTimeout(timer);
      try {
        URL.revokeObjectURL(tempUrl);
      } catch {}
      tempVideo.src = '';
    };

    tempVideo.onloadedmetadata = () => {
      const dur = tempVideo.duration || 0;
      cleanup();
      if (!resolved) {
        resolved = true;
        resolve(dur);
      }
    };

    tempVideo.onerror = () => {
      cleanup();
      if (!resolved) {
        resolved = true;
        resolve(0);
      }
    };

    try {
      tempVideo.src = tempUrl;
    } catch {
      cleanup();
      if (!resolved) {
        resolved = true;
        resolve(0);
      }
    }
  });
}

/**
 * Extract a short video clip locally using HTMLMediaElement.captureStream() and MediaRecorder.
 */
export async function extractClipWithBrowserCapture(
  sourceFile: File,
  startSeconds: number,
  endSeconds: number,
  onProgress?: (progress: BrowserCaptureProgress) => void,
  signal?: AbortSignal
): Promise<BrowserCaptureResult> {
  if (!isBrowserCaptureSupported()) {
    throw new Error(
      'Browser capture is not supported in this browser. Please use native FFmpeg command extraction or import an existing clip.'
    );
  }

  if (signal?.aborted) {
    throw new Error('Extraction was cancelled by user.');
  }

  const targetDuration = Math.max(0.1, endSeconds - startSeconds);
  const mimeType = getPreferredMimeType();
  const extension = mimeType.includes('mp4') ? 'mp4' : 'webm';
  const baseName = sourceFile.name.replace(/\.[^/.]+$/, '');
  const outputFilename = `browser_clip_${baseName}_${Math.round(startSeconds)}s_to_${Math.round(endSeconds)}s.${extension}`;

  const sourceObjectUrl = URL.createObjectURL(sourceFile);
  const video = document.createElement('video');
  video.muted = true;
  video.playsInline = true;
  video.preload = 'auto';

  let wasBackgroundThrottled = false;
  const onVisibilityChange = () => {
    if (document.hidden) {
      wasBackgroundThrottled = true;
    }
  };
  document.addEventListener('visibilitychange', onVisibilityChange);

  let stream: MediaStream | null = null;
  let recorder: MediaRecorder | null = null;
  const chunks: Blob[] = [];

  const cleanup = () => {
    document.removeEventListener('visibilitychange', onVisibilityChange);

    if (recorder && recorder.state !== 'inactive') {
      try {
        recorder.stop();
      } catch {}
    }

    if (stream) {
      stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {}
      });
      stream = null;
    }

    try {
      video.pause();
      video.src = '';
      video.load();
    } catch {}

    URL.revokeObjectURL(sourceObjectUrl);
  };

  try {
    // 1. Load source metadata
    await new Promise<void>((resolve, reject) => {
      const onMetadata = () => {
        video.removeEventListener('loadedmetadata', onMetadata);
        video.removeEventListener('error', onError);
        resolve();
      };
      const onError = () => {
        video.removeEventListener('loadedmetadata', onMetadata);
        video.removeEventListener('error', onError);
        reject(new Error('Failed to load local video metadata for browser capture.'));
      };
      video.addEventListener('loadedmetadata', onMetadata);
      video.addEventListener('error', onError);
      video.src = sourceObjectUrl;
    });

    if (signal?.aborted) throw new Error('Extraction cancelled.');

    // 2. Seek to starting boundary
    await new Promise<void>((resolve, reject) => {
      const onSeeked = () => {
        video.removeEventListener('seeked', onSeeked);
        video.removeEventListener('error', onError);
        resolve();
      };
      const onError = () => {
        video.removeEventListener('seeked', onSeeked);
        video.removeEventListener('error', onError);
        reject(new Error('Seeking to start timestamp failed.'));
      };
      video.addEventListener('seeked', onSeeked);
      video.addEventListener('error', onError);
      video.currentTime = startSeconds;
    });

    if (signal?.aborted) throw new Error('Extraction cancelled.');

    // 3. Capture stream and setup recorder
    if (typeof (video as any).captureStream === 'function') {
      stream = (video as any).captureStream();
    } else if (typeof (video as any).mozCaptureStream === 'function') {
      stream = (video as any).mozCaptureStream();
    }

    if (!stream) {
      throw new Error('captureStream() returned null or is unavailable.');
    }

    recorder = new MediaRecorder(stream, { mimeType });
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    // 4. Start recording and playback
    recorder.start(100);
    await video.play();

    // 5. Monitor progress until end boundary reached
    await new Promise<void>((resolve, reject) => {
      let intervalId: any = null;

      const stopRecording = () => {
        if (intervalId) clearInterval(intervalId);
        video.pause();

        if (recorder && recorder.state !== 'inactive') {
          recorder.onstop = () => resolve();
          recorder.stop();
        } else {
          resolve();
        }
      };

      intervalId = setInterval(() => {
        if (signal?.aborted) {
          if (intervalId) clearInterval(intervalId);
          cleanup();
          reject(new Error('Extraction cancelled by user.'));
          return;
        }

        const cur = video.currentTime;
        const elapsed = Math.max(0, cur - startSeconds);
        const percent = Math.min(100, Math.round((elapsed / targetDuration) * 100));

        if (onProgress) {
          onProgress({
            currentTime: cur,
            startSeconds,
            endSeconds,
            percent,
            statusText: `Recording (${percent}%)... Tab must remain visible.`,
          });
        }

        if (cur >= endSeconds || video.ended) {
          stopRecording();
        }
      }, 30);
    });

    // 6. Compile Blob into File
    const finalBlob = new Blob(chunks, { type: mimeType });
    const finalFile = new File([finalBlob], outputFilename, {
      type: mimeType,
      lastModified: Date.now(),
    });

    // 7. Measure actual duration
    const actualDuration = await measureVideoFileDuration(finalFile);
    const durationDelta = actualDuration > 0 ? actualDuration - targetDuration : 0;
    const finalObjectUrl = URL.createObjectURL(finalFile);

    let warningMessage: string | undefined = undefined;
    if (wasBackgroundThrottled) {
      warningMessage =
        'Browser tab was hidden or minimized during capture. Background frame throttling likely caused dropped frames or audio desynchronization.';
    } else {
      warningMessage = `Experimental capture produced ${actualDuration.toFixed(2)}s output vs ${targetDuration.toFixed(2)}s requested (delta: ${durationDelta >= 0 ? '+' : ''}${durationDelta.toFixed(2)}s). Browser MediaRecorder does not guarantee monotonic decoding timestamps. For ground-truth evidence in Whodunnit annotations, native FFmpeg extraction is strongly recommended.`;
    }

    cleanup();

    return {
      file: finalFile,
      objectUrl: finalObjectUrl,
      filename: outputFilename,
      sizeBytes: finalFile.size,
      actualDurationSeconds: actualDuration > 0 ? actualDuration : targetDuration,
      requestedDurationSeconds: targetDuration,
      durationDeltaSeconds: durationDelta,
      mimeType,
      wasBackgroundThrottled,
      warningMessage,
    };
  } catch (err) {
    cleanup();
    throw err;
  }
}
