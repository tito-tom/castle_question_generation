import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PREVIEW_FIXTURE = path.resolve(__dirname, 'fixtures/preview_test_6s.mp4');

test.describe('CASTLE QA Studio — Interval Preview and Mode C Browser Capture', () => {
  test.beforeAll(async () => {
    expect(fs.existsSync(PREVIEW_FIXTURE), `Test fixture missing: ${PREVIEW_FIXTURE}`).toBeTruthy();
  });

  test('Interval Preview: real playback bounds, seeking to 1.0s, boundary pause at 3.0s, and clearing interval', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[data-testid="open-local-video-btn"]')).toBeVisible({ timeout: 10000 });

    // 1. Load the 6s test fixture into the local video player
    const fileInput = page.locator('[data-testid="local-video-file-input"]');
    await fileInput.setInputFiles(PREVIEW_FIXTURE);
    await expect(page.getByText('Local video — Not uploaded').first()).toBeVisible({ timeout: 10000 });

    const videoElem = page.locator('[data-testid="video-element"]');
    await expect(videoElem).toBeVisible();

    // Wait until video has loaded metadata (duration > 0)
    await page.waitForFunction(() => {
      const v = document.querySelector('video') as HTMLVideoElement | null;
      return v && v.duration > 0;
    });

    // 2. Set interval to 1.000s -> 3.000s in ClipSelectionPanel
    const startInput = page.locator('[data-testid="start-timestamp-input"]');
    const endInput = page.locator('[data-testid="end-timestamp-input"]');
    await startInput.fill('00:00:01.000');
    await endInput.fill('00:00:03.000');

    // 3. Click "Preview Selection"
    const previewBtn = page.locator('[data-testid="preview-selection-btn"]');
    await expect(previewBtn).toBeVisible();
    await previewBtn.click();

    // Verify video element sought to ~1.0s and began playing
    await page.waitForFunction(() => {
      const v = document.querySelector('video') as HTMLVideoElement | null;
      return v && !v.paused && v.currentTime >= 0.95;
    }, { timeout: 10000 });

    // Verify playback advances
    await page.waitForTimeout(600);
    const midTime = await videoElem.evaluate((v: HTMLVideoElement) => v.currentTime);
    expect(midTime).toBeGreaterThan(1.0);

    // 4. Verify boundary pause at 3.0s
    // The player's handleTimeUpdate pauses at >= activeInterval.end and clamps to 3.0
    await page.waitForFunction(() => {
      const v = document.querySelector('video') as HTMLVideoElement | null;
      return v && v.paused && v.currentTime >= 2.95;
    }, { timeout: 10000 });

    const pausedAt = await videoElem.evaluate((v: HTMLVideoElement) => ({
      paused: v.paused,
      currentTime: v.currentTime,
    }));
    expect(pausedAt.paused).toBe(true);
    expect(pausedAt.currentTime).toBeGreaterThanOrEqual(2.95);
    expect(pausedAt.currentTime).toBeLessThanOrEqual(3.1);

    // 5. Clear active interval and resume playback
    const clearBtn = page.locator('[data-testid="clear-selection-btn"]');
    await clearBtn.click();

    // Play again using play button or video toggle
    const playPauseBtn = page.locator('button[title*="Play"], button[title*="Pause"]').first();
    await playPauseBtn.click();

    // Verify normal playback resumes and advances beyond 3.1s
    await page.waitForFunction(() => {
      const v = document.querySelector('video') as HTMLVideoElement | null;
      return v && !v.paused && v.currentTime > 3.1;
    }, { timeout: 10000 });
  });

  test('Mode C: Experimental Browser Capture (MediaRecorder/captureStream), Cancellation, and Delta Warning', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[data-testid="open-local-video-btn"]')).toBeVisible({ timeout: 10000 });

    // 1. Load the 6s test fixture
    const fileInput = page.locator('[data-testid="local-video-file-input"]');
    await fileInput.setInputFiles(PREVIEW_FIXTURE);
    await expect(page.getByText('Local video — Not uploaded').first()).toBeVisible({ timeout: 10000 });

    // 2. Set interval to 1.0s -> 2.5s (1.5s interval)
    await page.locator('[data-testid="start-timestamp-input"]').fill('00:00:01.000');
    await page.locator('[data-testid="end-timestamp-input"]').fill('00:00:02.500');

    // 3. Open Extraction Modal
    const extractBtn = page.locator('[data-testid="extract-clip-btn"]');
    await extractBtn.click();

    // Switch to Mode C tab
    const modeCTab = page.locator('[data-testid="tab-mode-c"]');
    await expect(modeCTab).toBeVisible();
    await modeCTab.click();

    // Verify experimental warning is visible
    await expect(page.locator('[data-testid="browser-capture-warning"]')).toBeVisible();
    await expect(page.getByText('Experimental Feature Notice')).toBeVisible();

    // 4. Test Cancellation: Start capture then immediately cancel
    const startCaptureBtn = page.locator('[data-testid="start-browser-capture-btn"]');
    await expect(startCaptureBtn).toBeVisible();
    await startCaptureBtn.click();

    const cancelBtn = page.locator('[data-testid="cancel-capture-btn"]');
    await expect(cancelBtn).toBeVisible({ timeout: 5000 });
    await cancelBtn.click();

    // Verify cancellation notice
    await expect(page.getByText('Capture was cancelled.')).toBeVisible({ timeout: 5000 });

    // 5. Test Full Real In-Browser Capture of 1.5s interval
    await page.waitForTimeout(500);
    // Restart capture
    const retryStartBtn = page.locator('[data-testid="start-browser-capture-btn"]');
    await expect(retryStartBtn).toBeVisible();
    await retryStartBtn.click();

    // Wait for capture to complete (plays ~1.5s + processing)
    const stageCaptureBtn = page.locator('[data-testid="confirm-browser-capture-btn"]');
    await expect(stageCaptureBtn).toBeVisible({ timeout: 20000 });

    // Verify duration measurement and delta warning
    await expect(page.locator('[data-testid="capture-result-warning"]')).toBeVisible();
    await expect(page.getByText('Experimental Browser Capture Warning')).toBeVisible();

    // 6. Confirm and stage the captured clip
    await stageCaptureBtn.click();

    // Verify StagedClipCard appears
    const stagedCard = page.locator('[data-testid="staged-clip-video-player"]');
    await expect(stagedCard).toBeVisible({ timeout: 5000 });

    // Verify browser_capture method badge and approximate alignment badge
    await expect(page.getByText('Browser Capture (Experimental)')).toBeVisible();
    await expect(page.getByText('Alignment: Approximate')).toBeVisible();
  });
});
