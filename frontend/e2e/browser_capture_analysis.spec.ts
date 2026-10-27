import { test, expect } from '@playwright/test';
import { execFileSync, spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SOURCE_VIDEO = path.resolve(__dirname, '../../data/videos/kitchen_8_day_1.mp4');
const REPO_ROOT = path.resolve(__dirname, '../..');

function runMediaTool(tool: 'ffprobe' | 'ffmpeg', args: string[]): string {
  const mountPath = REPO_ROOT.replaceAll('\\', '/');
  return execFileSync('docker', [
    'run', '--rm', '-v', `${mountPath}:/validation:ro`, 'castle-qa-api:latest', tool, ...args,
  ], { encoding: 'utf8' });
}

function readMediaProbe(relativePath: string) {
  return JSON.parse(runMediaTool('ffprobe', [
    '-v', 'error', '-show_streams', '-show_format',
    '-show_entries', 'stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,duration,start_time,sample_rate:format=format_name,duration',
    '-of', 'json', `/validation/${relativePath.replaceAll('\\', '/')}`,
  ]));
}

function readFrameTimestamps(relativePath: string, interval?: string): number[] {
  const args = ['-v', 'error'];
  if (interval) args.push('-read_intervals', interval);
  args.push(
    '-select_streams', 'v:0', '-show_frames',
    '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json',
    `/validation/${relativePath.replaceAll('\\', '/')}`,
  );
  const probe = JSON.parse(runMediaTool('ffprobe', args));
  return (probe.frames || [])
    .map((frame: { best_effort_timestamp_time?: string }) => Number(frame.best_effort_timestamp_time))
    .filter(Number.isFinite);
}

function readConsecutiveDuplicateFrames(relativePath: string, sourceStartSeconds?: number, sourceDurationSeconds?: number): number {
  const args = ['-v', 'error'];
  if (sourceStartSeconds !== undefined) args.push('-ss', String(sourceStartSeconds));
  args.push('-i', `/validation/${relativePath.replaceAll('\\', '/')}`);
  if (sourceDurationSeconds !== undefined) args.push('-t', String(sourceDurationSeconds));
  args.push('-map', '0:v:0', '-f', 'framemd5', '-');
  const output = runMediaTool('ffmpeg', args);
  const hashes = output.split(/\r?\n/)
    .filter((line) => line && !line.startsWith('#'))
    .map((line) => line.split(',').at(-1)?.trim())
    .filter((hash): hash is string => Boolean(hash));
  return hashes.slice(1).filter((hash, index) => hash === hashes[index]).length;
}

function readAudioLevels(relativePath: string, sourceStartSeconds?: number, sourceDurationSeconds?: number) {
  const args = ['run', '--rm', '-v', `${REPO_ROOT.replaceAll('\\', '/')}:/validation:ro`, 'castle-qa-api:latest', 'ffmpeg', '-v', 'info'];
  if (sourceStartSeconds !== undefined) args.push('-ss', String(sourceStartSeconds));
  args.push('-i', `/validation/${relativePath.replaceAll('\\', '/')}`, '-map', '0:a:0');
  if (sourceDurationSeconds !== undefined) args.push('-t', String(sourceDurationSeconds));
  args.push('-af', 'volumedetect', '-f', 'null', '-');
  const result = spawnSync('docker', args, { encoding: 'utf8' });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`FFmpeg audio analysis failed: ${result.stderr}`);
  const log = `${result.stdout || ''}\n${result.stderr || ''}`;
  return {
    meanVolumeDb: log.match(/mean_volume:\s*(-?[\d.]+) dB/)?.[1] ?? null,
    maxVolumeDb: log.match(/max_volume:\s*(-?[\d.]+) dB/)?.[1] ?? null,
  };
}

function summarizeFrames(timestamps: number[]) {
  const sorted = timestamps.slice().sort((a, b) => a - b);
  const deltas = sorted.slice(1).map((timestamp, index) => timestamp - sorted[index]);
  const positiveDeltas = deltas.filter((delta) => delta > 0);
  const medianDelta = positiveDeltas.slice().sort((a, b) => a - b)[Math.floor(positiveDeltas.length / 2)] || 0;
  return {
    frameCount: sorted.length,
    firstPts: sorted[0],
    lastPts: sorted[sorted.length - 1],
    effectiveFps: sorted.length > 1 ? (sorted.length - 1) / (sorted[sorted.length - 1] - sorted[0]) : 0,
    medianFrameDelta: medianDelta,
    duplicatePts: deltas.filter((delta) => delta <= 0).length,
    largeGaps: medianDelta > 0 ? deltas.filter((delta) => delta > medianDelta * 1.5).length : 0,
  };
}

test('15-second Browser Capture stages, uploads only the short clip, and completes through the mock worker', async ({ page }) => {
  expect(fs.existsSync(SOURCE_VIDEO), `CASTLE fixture missing: ${SOURCE_VIDEO}`).toBeTruthy();
  const sourceSize = fs.statSync(SOURCE_VIDEO).size;
  const sourceProbe = readMediaProbe('data/videos/kitchen_8_day_1.mp4');
  const sourceVideoStream = sourceProbe.streams.find((stream: any) => stream.codec_type === 'video');
  expect(sourceVideoStream).toBeTruthy();

  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.locator('[data-testid="local-video-file-input"]').setInputFiles(SOURCE_VIDEO);
  await expect(page.getByText('Local video — Not uploaded').first()).toBeVisible();
  await page.waitForFunction(() => {
    const video = document.querySelector('[data-testid="video-element"]') as HTMLVideoElement | null;
    return video && Number.isFinite(video.duration) && video.duration > 315;
  });

  await page.locator('[data-testid="start-timestamp-input"]').fill('00:05:00.000');
  await page.locator('[data-testid="end-timestamp-input"]').fill('00:05:15.000');
  await page.locator('[data-testid="extract-clip-btn"]').click();
  await page.locator('[data-testid="tab-mode-c"]').click();
  await expect(page.locator('[data-testid="start-browser-capture-btn"]')).toBeEnabled();
  await page.locator('[data-testid="start-browser-capture-btn"]').click();
  const stageButton = page.locator('[data-testid="confirm-browser-capture-btn"]');
  await expect(stageButton).toBeVisible({ timeout: 45000 });
  await expect(page.locator('[data-testid="capture-ready-for-staging"]')).toContainText('Validated');
  const captureValidationText = await page.locator('[data-testid="capture-ready-for-staging"]').innerText();
  const validatedMime = captureValidationText.match(/Validated (video\/(?:mp4|webm))/)?.[1];
  expect(validatedMime).toBeTruthy();

  const stageTriggeredDownload = page.waitForEvent('download', { timeout: 1000 }).then(() => true).catch(() => false);
  await stageButton.click();
  expect(await stageTriggeredDownload).toBe(false);
  await expect(page.locator('[data-testid="clip-extraction-modal"]')).not.toBeVisible();
  const stagedVideo = page.locator('[data-testid="staged-clip-video-player"]');
  await expect(stagedVideo).toBeVisible();
  await stagedVideo.evaluate(async (video: HTMLVideoElement) => {
    await new Promise<void>((resolve, reject) => {
      if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) return resolve();
      const timer = setTimeout(() => reject(new Error('staged clip frame did not decode')), 10000);
      video.addEventListener('loadeddata', () => { clearTimeout(timer); resolve(); }, { once: true });
      video.addEventListener('error', () => { clearTimeout(timer); reject(new Error('staged clip decode failed')); }, { once: true });
    });
  });

  const analyze = page.locator('[data-testid="upload-to-qwen-btn"]');
  await expect(analyze).toBeEnabled();
  const playbackRateText = await page.locator('[data-testid="staged-clip-capture-playback-rate"]').innerText();
  const capturePlaybackRate = Number(playbackRateText.replace('x', ''));
  expect(capturePlaybackRate).toBe(1);
  const captureWallClockText = await page.locator('[data-testid="staged-clip-capture-wall-time"]').innerText();
  const captureWallClockSeconds = Number(captureWallClockText.replace('s', ''));

  // The download is optional in the product flow. Trigger it alongside Analyze so the
  // workflow proves analysis can start without waiting for or depending on a download.
  const downloadPromise = Promise.all([
    page.waitForEvent('download'),
    page.locator('[data-testid="download-staged-clip-btn"]').click(),
  ]).then(([download]) => download);
  const requestPromise = page.waitForRequest((request) => request.method() === 'POST' && request.url().includes('/videos/upload-clip'));
  const responsePromise = page.waitForResponse((response) => response.request().method() === 'POST' && response.url().includes('/videos/upload-clip'));
  const clickPromise = analyze.click();
  const [uploadRequest, uploadResponse] = await Promise.all([
    requestPromise,
    responsePromise,
  ]);
  await clickPromise;
  const download = await downloadPromise;
  const downloadedFilename = download.suggestedFilename();
  const downloadedPath = await download.path();
  expect(downloadedPath).toBeTruthy();
  const savedPath = path.join(REPO_ROOT, 'frontend', 'test-results', downloadedFilename);
  fs.mkdirSync(path.dirname(savedPath), { recursive: true });
  await download.saveAs(savedPath);
  const downloadedSize = fs.statSync(savedPath).size;
  expect(downloadedSize).toBeGreaterThan(0);

  const captureRelativePath = path.relative(REPO_ROOT, savedPath);
  const captureProbe = readMediaProbe(captureRelativePath);
  const captureVideoStream = captureProbe.streams.find((stream: any) => stream.codec_type === 'video');
  const captureAudioStream = captureProbe.streams.find((stream: any) => stream.codec_type === 'audio');
  expect(captureVideoStream).toBeTruthy();
  expect(captureVideoStream.width).toBeGreaterThan(0);
  expect(captureVideoStream.height).toBeGreaterThan(0);
  expect(captureVideoStream.codec_name).toBeTruthy();
  const capturedFormat = String(captureProbe.format.format_name);
  const detectedExtension = capturedFormat.includes('mp4') ? '.mp4' : capturedFormat.includes('webm') ? '.webm' : '';
  expect(detectedExtension).toBeTruthy();
  expect(path.extname(downloadedFilename).toLowerCase()).toBe(detectedExtension);
  expect(validatedMime).toBe(detectedExtension === '.mp4' ? 'video/mp4' : 'video/webm');
  const captureDuration = Number(captureProbe.format.duration);
  expect(captureDuration).toBeGreaterThan(0);
  expect(captureDuration).toBeLessThanOrEqual(120);
  execFileSync('docker', [
    'run', '--rm', '-v', `${REPO_ROOT.replaceAll('\\', '/')}:/validation:ro`, 'castle-qa-api:latest',
    'ffmpeg', '-v', 'error', '-i', `/validation/${captureRelativePath.replaceAll('\\', '/')}`, '-f', 'null', '-',
  ], { stdio: 'pipe' });

  const sourceFrames = readFrameTimestamps('data/videos/kitchen_8_day_1.mp4', '300%+20')
    .filter((pts) => pts >= 300 && pts <= 315);
  const captureFrames = readFrameTimestamps(captureRelativePath);
  const timing = {
    sourceIntervalSeconds: '300-315',
    sourceCodec: sourceVideoStream.codec_name,
    sourceAvgFps: sourceVideoStream.avg_frame_rate,
    sourceFormat: sourceProbe.format.format_name,
    sourceFrames: summarizeFrames(sourceFrames),
    captureMime: validatedMime,
    captureFormat: capturedFormat,
    captureCodec: captureVideoStream.codec_name,
    captureAvgFps: captureVideoStream.avg_frame_rate,
    captureVideoStreamDurationSeconds: captureVideoStream.duration,
    captureDurationSeconds: captureDuration,
    recorderWallClockSeconds: captureWallClockSeconds,
    playbackRate: capturePlaybackRate,
    captureFrames: summarizeFrames(captureFrames),
    sourceAudioStream: sourceProbe.streams.find((stream: any) => stream.codec_type === 'audio') || null,
    captureAudioStream: captureAudioStream || null,
    sourceAudioLevels: readAudioLevels('data/videos/kitchen_8_day_1.mp4', 300, 15),
    captureAudioLevels: readAudioLevels(captureRelativePath),
    sourceConsecutiveDuplicateFrames: readConsecutiveDuplicateFrames('data/videos/kitchen_8_day_1.mp4', 300, 15),
    captureConsecutiveDuplicateFrames: readConsecutiveDuplicateFrames(captureRelativePath),
  };
  console.log(`[CAPTURE_TIMING] ${JSON.stringify(timing)}`);

  expect(uploadResponse.status()).toBe(201);
  const uploadedClip = await uploadResponse.json();
  expect(uploadedClip.is_temporary).toBe(true);
  expect(uploadedClip.size_bytes).toBeGreaterThan(0);
  expect(uploadedClip.size_bytes).toBe(downloadedSize);
  expect(uploadedClip.size_bytes).toBeLessThanOrEqual(200 * 1024 * 1024);
  expect(uploadedClip.duration_seconds).toBeGreaterThan(0);
  expect(uploadedClip.duration_seconds).toBeLessThanOrEqual(120);
  expect(uploadRequest.url()).toContain('/videos/upload-clip');
  expect(uploadedClip.size_bytes).toBeLessThan(sourceSize * 0.01);

  const mockBanner = page.locator('[data-testid="mock-inference-banner"]');
  await expect(mockBanner).toBeVisible({ timeout: 45000 });
  await expect(mockBanner).toContainText('MOCK / TEST DATA');
  await expect(page.getByText('Chronological Event Timeline')).toBeVisible();
  await expect(page.locator('[data-testid="event-clip-time"]').first()).toBeVisible();
  await expect(page.getByText('Temporary Clip')).toBeVisible();
});
