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
  captureWallClockSeconds: number;
  capturePlaybackRate: number;
  mimeType: string;
  wasBackgroundThrottled: boolean;
  warningMessage?: string;
}

export interface ValidatedVideoMetadata {
  durationSeconds: number;
  width: number;
  height: number;
  mimeType: string;
}

/** Decode and briefly play/seek a local video before allowing it to be staged. */
export async function validateVideoFile(file: File, timeoutMs = 10000): Promise<ValidatedVideoMetadata> {
  if (!(file instanceof Blob) || file.size <= 0) throw new Error('Captured video is empty. Retry capture or use Native FFmpeg.');
  const mime = file.type.toLowerCase();
  if (!mime.startsWith('video/') || (!mime.includes('mp4') && !mime.includes('webm'))) {
    throw new Error(`Unsupported captured media format (${mime || 'unknown'}). Use Native FFmpeg or Import Existing Clip.`);
  }

  const url = URL.createObjectURL(file);
  const video = document.createElement('video');
  video.muted = true;
  video.preload = 'auto';
  video.playsInline = true;
  try {
    await new Promise<void>((resolve, reject) => {
      const timer = window.setTimeout(() => reject(new Error('Timed out while decoding captured video. Retry or use Native FFmpeg.')), timeoutMs);
      const cleanup = () => { clearTimeout(timer); video.removeEventListener('loadedmetadata', metadata); video.removeEventListener('loadeddata', loaded); video.removeEventListener('error', failed); };
      const metadata = () => {
        if (video.videoWidth <= 0 || video.videoHeight <= 0) {
          cleanup();
          reject(new Error(`Captured media has no decodable video track (${video.videoWidth}x${video.videoHeight}). Retry or use Native FFmpeg.`));
        }
      };
      const loaded = () => { cleanup(); resolve(); };
      const failed = () => { cleanup(); reject(new Error('Captured video could not be decoded by this browser. Retry or use Native FFmpeg.')); };
      video.addEventListener('loadedmetadata', metadata, { once: true });
      video.addEventListener('loadeddata', loaded, { once: true });
      video.addEventListener('error', failed, { once: true });
      video.src = url;
      video.load();
    });

    // Some valid MediaRecorder WebM files report duration=Infinity, but expose
    // a finite end through the media element's seekable ranges.
    const duration = Number.isFinite(video.duration)
      ? video.duration
      : video.seekable.length > 0
        ? video.seekable.end(video.seekable.length - 1)
        : NaN;
    if (!Number.isFinite(duration) || duration <= 0 || video.videoWidth <= 0 || video.videoHeight <= 0) {
      throw new Error('Captured video has no valid video track or duration. Retry or use Native FFmpeg.');
    }
    // loadeddata confirms a decoded frame; seek and play briefly to catch broken media ranges.
    if (duration > 0.1) {
      await new Promise<void>((resolve, reject) => {
        const timer = window.setTimeout(() => reject(new Error('Captured video could not seek. Retry or use Native FFmpeg.')), timeoutMs);
        const done = () => { clearTimeout(timer); video.removeEventListener('seeked', done); video.removeEventListener('error', failed); resolve(); };
        const failed = () => { clearTimeout(timer); video.removeEventListener('seeked', done); reject(new Error('Captured video failed during seek. Retry or use Native FFmpeg.')); };
        video.addEventListener('seeked', done, { once: true });
        video.addEventListener('error', failed, { once: true });
        video.currentTime = Math.min(0.05, duration / 2);
      });
      try { await video.play(); } catch { throw new Error('Captured video could not play after decoding. Retry or use Native FFmpeg.'); }
      video.pause();
    }
    return { durationSeconds: duration, width: video.videoWidth, height: video.videoHeight, mimeType: mime };
  } finally {
    video.pause();
    video.removeAttribute('src');
    video.load();
    URL.revokeObjectURL(url);
  }
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
    'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
    'video/mp4;codecs=avc1',
    'video/mp4',
    'video/webm;codecs=vp8,opus',
    'video/webm;codecs=vp9,opus',
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

  return '';
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
  if (!mimeType) throw new Error('This browser cannot record a supported MP4 or WebM format. Use Native FFmpeg or Import Existing Clip.');
  if (targetDuration > 120) throw new Error('This interval exceeds the current 120-second Qwen limit. Select a shorter interval or use Import Existing Clip for local processing.');
  const baseName = sourceFile.name.replace(/\.[^/.]+$/, '');
  let outputFilename = '';

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
    const actualMimeType = recorder.mimeType || mimeType;
    const normalizedMime = actualMimeType.toLowerCase();
    const extension = normalizedMime.includes('mp4') ? 'mp4' : normalizedMime.includes('webm') ? 'webm' : '';
    if (!extension || !normalizedMime.startsWith('video/')) {
      throw new Error(`Browser selected unsupported recording format (${actualMimeType || 'unknown'}). Use Native FFmpeg or Import Existing Clip.`);
    }
    outputFilename = `browser_clip_${baseName}_${Math.round(startSeconds)}s_to_${Math.round(endSeconds)}s.${extension}`;
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    // 4. Start recording and playback
    const recordingStartedAt = performance.now();
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
    const captureWallClockSeconds = (performance.now() - recordingStartedAt) / 1000;

    onProgress?.({ currentTime: endSeconds, startSeconds, endSeconds, percent: 100, statusText: 'Finalizing recorded media...' });
    // 6. Compile Blob into File
    const finalBlob = new Blob(chunks, { type: actualMimeType });
    const finalFile = new File([finalBlob], outputFilename, {
      type: actualMimeType,
      lastModified: Date.now(),
    });

    // 7. Measure actual duration
    onProgress?.({ currentTime: endSeconds, startSeconds, endSeconds, percent: 100, statusText: 'Validating video decode, frame, seek and playback...' });
    const validated = await validateVideoFile(finalFile);
    const actualDuration = validated.durationSeconds;
    const durationDelta = actualDuration - targetDuration;
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
      captureWallClockSeconds,
      capturePlaybackRate: video.playbackRate,
      mimeType: actualMimeType,
      wasBackgroundThrottled,
      warningMessage,
    };
  } catch (err) {
    cleanup();
    throw err;
  }
}
