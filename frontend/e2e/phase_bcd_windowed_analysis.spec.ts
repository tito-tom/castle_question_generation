import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createAnalysisWindows, formatWindowOutputName } from '../src/features/videos/analysisWindows';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '../..');
const SOURCE_VIDEO = path.join(REPO_ROOT, 'data', 'videos', 'kitchen_8_day_1.mp4');
const E2E_STATE = path.join(REPO_ROOT, 'frontend', '.playwright-e2e-state.json');

function timestamp(seconds: number): string {
  const whole = Math.floor(seconds);
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const remainder = seconds % 60;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${remainder.toFixed(3).padStart(6, '0')}`;
}

function createNativeTestWindows(outputDir: string, windows: ReturnType<typeof createAnalysisWindows>, filenames: string[]) {
  fs.mkdirSync(outputDir, { recursive: true });
  const mountRoot = REPO_ROOT.replaceAll('\\', '/');
  const mountOutput = outputDir.replaceAll('\\', '/');
  for (let index = 0; index < windows.length; index += 1) {
    const window = windows[index];
    execFileSync('docker', [
      'run', '--rm',
      '-v', `${mountRoot}:/source:ro`,
      '-v', `${mountOutput}:/clips`,
      'castle-qa-api:latest', 'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
      '-ss', timestamp(window.startSeconds), '-to', timestamp(window.endSeconds),
      '-i', '/source/data/videos/kitchen_8_day_1.mp4',
      '-map', '0:v:0', '-map', '0:a?',
      '-vf', 'fps=2,scale=320:-2', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '35',
      '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart',
      `/clips/${filenames[index]}`,
    ], { cwd: REPO_ROOT, stdio: 'pipe' });
  }
}

test('local multi-minute interval imports, analyzes and merges with temporary media cleanup', async ({ page }) => {
  test.setTimeout(300000);
  expect(fs.existsSync(SOURCE_VIDEO), `CASTLE source recording missing: ${SOURCE_VIDEO}`).toBeTruthy();
  expect(fs.existsSync(E2E_STATE), 'Isolated E2E harness state was not created.').toBeTruthy();
  const sourceBefore = fs.statSync(SOURCE_VIDEO);
  const state = JSON.parse(fs.readFileSync(E2E_STATE, 'utf8')) as { runDir: string };
  const outputDir = path.join(state.runDir, 'analysis-windows');
  const windows = createAnalysisWindows(300, 480);
  const outputNames = windows.map((window) => formatWindowOutputName(path.basename(SOURCE_VIDEO), window));
  createNativeTestWindows(outputDir, windows, outputNames);
  const clipPaths = outputNames.map((name) => path.join(outputDir, name));
  clipPaths.forEach((clipPath) => expect(fs.statSync(clipPath).size).toBeLessThan(200 * 1024 * 1024));

  await page.goto('/');
  await page.locator('[data-testid="local-video-file-input"]').setInputFiles(SOURCE_VIDEO);
  await expect(page.locator('[data-testid="video-element"]')).toBeVisible();
  await expect(page.getByText('Local video — Not uploaded').first()).toBeVisible();

  await page.locator('[data-testid="start-timestamp-input"]').fill(timestamp(300));
  await page.locator('[data-testid="end-timestamp-input"]').fill(timestamp(480));
  await expect(page.locator('[data-testid="start-timestamp-input"]')).toHaveValue(timestamp(300));
  await expect(page.locator('[data-testid="end-timestamp-input"]')).toHaveValue(timestamp(480));
  await page.locator('[data-testid="extract-clip-btn"]').click();
  const preparation = page.locator('[data-testid="windowed-preparation-modal"]');
  await expect(preparation).toBeVisible();
  await expect(preparation.getByText('3 overlapping clips')).toBeVisible();
  await expect(preparation.getByText('Browsers cannot run native FFmpeg.')).toBeVisible();
  await preparation.locator('[data-testid="windowed-files-input"]').setInputFiles(clipPaths);
  await expect(preparation.getByText(/clip_kitchen_8_day_1_w01_/i)).toBeVisible({ timeout: 30000 });
  await expect(preparation.getByRole('button', { name: 'Prepare 3 clips for analysis' })).toBeEnabled();
  await preparation.getByRole('button', { name: 'Prepare 3 clips for analysis' }).click();

  const batchCard = page.locator('[data-testid="windowed-clip-batch"]');
  await expect(batchCard).toBeVisible();
  await expect(batchCard.locator('[data-testid="analysis-window-1"]')).toContainText('00:05:00.000');
  await expect(batchCard.locator('[data-testid="analysis-window-2"]')).toContainText('00:06:20.000');
  await expect(batchCard.locator('[data-testid="analysis-window-3"]')).toContainText('00:07:40.000');

  const uploads: Array<Record<string, any>> = [];
  const mergedResults: Array<Record<string, any>> = [];
  page.on('response', (response) => {
    if (response.url().includes('/api/v1/videos/upload-clip') && response.status() === 201) {
      void response.json().then((data) => uploads.push(data));
    }
    if (response.url().includes('/api/v1/analyses/merge-windows') && response.status() === 200) {
      void response.json().then((data) => mergedResults.push(data));
    }
  });
  await batchCard.getByRole('button', { name: 'Analyze Selected Interval' }).click();
  await expect(page.locator('[data-testid="mock-inference-banner"]')).toBeVisible({ timeout: 120000 });
  await expect(batchCard).toContainText('Temporary uploads deleted.', { timeout: 30000 });
  await expect.poll(() => uploads.length, { timeout: 30000 }).toBe(3);
  expect(uploads.every((upload) => upload.is_temporary === true)).toBeTruthy();
  const uploadedFileSizes = uploads.map((upload) => Number(upload.size_bytes));
  expect(uploadedFileSizes.every((size) => size > 0 && size < 200 * 1024 * 1024)).toBeTruthy();
  expect(uploadedFileSizes.every((size) => size < sourceBefore.size * 0.01)).toBeTruthy();

  await expect.poll(() => mergedResults.length, { timeout: 30000 }).toBe(1);
  const mergedId = mergedResults[0].analysis_id as string;
  const apiBase = new URL('/api/v1/', page.url()).toString();
  const mergedAnalysisResponse = await page.request.get(`${apiBase}analyses/${mergedId}`, {
    headers: { 'X-Session-Token': uploads[0].session_token },
  });
  expect(mergedAnalysisResponse.ok()).toBeTruthy();
  const mergedAnalysis = await mergedAnalysisResponse.json();
  expect(mergedAnalysis.window_analysis_ids).toHaveLength(3);
  expect(mergedAnalysis.events.length).toBeGreaterThan(0);
  expect(mergedAnalysis.events.every((event: any) => event.source_start_seconds >= 300 && event.source_end_seconds <= 480)).toBeTruthy();
  expect(mergedAnalysis.is_mock).toBe(true);

  for (const upload of uploads) {
    const mediaResponse = await page.request.get(`${apiBase}videos/${upload.video_id}`, {
      headers: { 'X-Session-Token': upload.session_token },
    });
    expect(mediaResponse.status()).toBe(404);
  }
  for (const windowAnalysisId of mergedAnalysis.window_analysis_ids) {
    const windowResponse = await page.request.get(`${apiBase}analyses/${windowAnalysisId}`, {
      headers: { 'X-Session-Token': uploads[0].session_token },
    });
    expect(windowResponse.ok()).toBeTruthy();
    expect((await windowResponse.json()).video_available).toBe(false);
  }
  await expect(page.locator('[data-testid="event-source-time"]').first()).toContainText('Source: 05:');

  await expect(page.getByRole('button', { name: 'Video Understanding' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Generate Questions' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Grounded Video QA' })).toHaveCount(0);
  await expect(page.getByText('Whodunnit Review Workspace')).toHaveCount(0);
  await expect(page.locator('[data-testid="grounded-qa-input"]')).toHaveCount(0);
  const finalAnalysis = await page.request.get(`${apiBase}analyses/${mergedId}`, {
    headers: { 'X-Session-Token': uploads[0].session_token },
  });
  expect(finalAnalysis.ok()).toBeTruthy();
  const sourceAfter = fs.statSync(SOURCE_VIDEO);
  expect(sourceAfter.size).toBe(sourceBefore.size);
  expect(sourceAfter.mtimeMs).toBe(sourceBefore.mtimeMs);
});
