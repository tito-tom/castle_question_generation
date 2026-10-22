import { test, expect, Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const VIDEO_PATH = path.resolve(__dirname, '../../data/videos/kitchen_8_day_1.mp4');
const CLIP_PATH = path.resolve(__dirname, '../../data/clips/extracted_kitchen_8_day_1_120_145.mp4');

test.describe.serial('CASTLE QA Studio — Laptop E2E Test Suite (Tests A to K)', () => {
  let page: Page;
  const consoleErrors: string[] = [];
  const uncaughtErrors: Error[] = [];
  let largeNetworkPayloads: { url: string; method: string; size: number }[] = [];

  test.beforeAll(async ({ browser }) => {
    // Verify test media files exist
    expect(fs.existsSync(VIDEO_PATH), `Local video file missing: ${VIDEO_PATH}`).toBeTruthy();
    expect(fs.existsSync(CLIP_PATH), `Extracted clip file missing: ${CLIP_PATH}`).toBeTruthy();

    const context = await browser.newContext({
      permissions: ['clipboard-read', 'clipboard-write'],
      acceptDownloads: true,
    });
    page = await context.newPage();

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (err) => {
      uncaughtErrors.push(err);
    });

    // Monitor for any accidental upload of the 1.28 GB video
    page.on('request', (request) => {
      const buffer = request.postDataBuffer();
      if (buffer && buffer.length > 1_000_000) {
        // Any request > 1MB is flagged
        largeNetworkPayloads.push({
          url: request.url(),
          method: request.method(),
          size: buffer.length,
        });
      }
    });
  });

  test.afterAll(async () => {
    await page.context().close();
  });

  // --------------------------------------------------------------------------
  // Test A — Frontend Startup
  // --------------------------------------------------------------------------
  test('Test A — Frontend loads cleanly with initial empty workspace', async () => {
    await page.goto('/');

    // Verify page header
    const headerTitle = page.locator('header h1');
    await expect(headerTitle).toContainText('CASTLE QA Studio');

    // Verify main workspace controls render
    await expect(page.locator('[data-testid="open-local-video-btn"]')).toBeVisible();

    // Verify navigation tabs
    await expect(page.getByRole('button', { name: 'Video Understanding' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Generate Questions' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Grounded Video QA' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Whodunnit Review' })).toHaveCount(0);

    // No uncaught runtime exceptions
    expect(uncaughtErrors.length).toBe(0);
  });

  // --------------------------------------------------------------------------
  // Test B — Local Video Selection & Playback (ZERO Original-Video Upload)
  // --------------------------------------------------------------------------
  test('Test B — Local CASTLE video selection, playback, seeking with ZERO network upload', async () => {
    // Clear any previous payload records
    largeNetworkPayloads = [];
    let uploadEndpointsHit = 0;

    const requestListener = (req: any) => {
      if (req.url().includes('/api/v1/videos/upload') && req.method() === 'POST') {
        uploadEndpointsHit++;
      }
    };
    page.on('request', requestListener);

    // Provide the 1.28 GB video via file input
    const fileInput = page.locator('[data-testid="local-video-file-input"]');
    await fileInput.setInputFiles(VIDEO_PATH);

    // Verify local video badge and filename display
    await expect(page.getByText('Local video — Not uploaded').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('kitchen_8_day_1.mp4').first()).toBeVisible();

    // Verify video element source uses a blob: URL
    const videoElem = page.locator('[data-testid="video-element"]');
    await expect(videoElem).toBeVisible();
    const videoSrc = await videoElem.getAttribute('src');
    expect(videoSrc).toBeTruthy();
    expect(videoSrc?.startsWith('blob:')).toBeTruthy();

    // Verify video duration is ~3600s (01:00:00)
    const timeDisplay = page.locator('[data-testid="video-time-display"]');
    await expect(timeDisplay).toBeVisible();
    await expect(timeDisplay).toContainText('01:00:00');

    // Test Play / Pause control
    const playPauseBtn = page.locator('button[title="Play"], button[title="Pause"]').first();
    await expect(playPauseBtn).toBeVisible();
    await playPauseBtn.click();
    await page.waitForTimeout(600); // Allow brief playback
    await playPauseBtn.click(); // Pause

    // CRITICAL PRIVACY ASSERTION: Opening, playing, and inspecting the 1.28 GB video caused ZERO network upload
    expect(uploadEndpointsHit).toBe(0);
    expect(largeNetworkPayloads.length).toBe(0);

    page.off('request', requestListener);
  });

  // --------------------------------------------------------------------------
  // Test C — Timestamp Interval Selection & Boundary Validation
  // --------------------------------------------------------------------------
  test('Test C — Interval selection (120s to 145s = 25s) with boundary validation', async () => {
    // 1. Test validation error: negative or invalid order (end before start)
    const startInput = page.locator('[data-testid="start-timestamp-input"]');
    const endInput = page.locator('[data-testid="end-timestamp-input"]');
    const addSelectionBtn = page.locator('[data-testid="add-selection-btn"]');

    await startInput.fill('00:02:30.000'); // 150s
    await endInput.fill('00:02:00.000'); // 120s
    await addSelectionBtn.click();

    // Validation error must appear
    const validationError = page.locator('[data-testid="selection-validation-error"]');
    await expect(validationError).toBeVisible();
    await expect(validationError).toContainText('greater than start timestamp');

    // 2. Set valid 120s -> 145s interval
    await startInput.fill('00:02:00.000'); // 120s
    await endInput.fill('00:02:25.000'); // 145s
    await page.locator('[data-testid="selection-label-input"]').fill('Kitchen Activity (120s-145s)');

    // Error should be dismissed
    await expect(validationError).not.toBeVisible();

    // Verify calculated duration indicator: 25.0s
    await expect(page.getByText('Selected Interval: 25.0s')).toBeVisible();

    // Save selection
    await addSelectionBtn.click();

    // Verify saved interval listed
    await expect(page.getByText('Saved Intervals (1)')).toBeVisible();
    await expect(page.getByText('Kitchen Activity (120s-145s)')).toBeVisible();

    // Preview selection
    const previewBtn = page.locator('[data-testid="preview-selection-btn"]');
    await previewBtn.click();

    // Verify active interval overlay is displayed
    const overlay = page.locator('[data-testid="active-interval-overlay"]');
    await expect(overlay).toBeVisible();
    await expect(overlay).toContainText('00:02:00.000 – 00:02:25.000');
  });

  // --------------------------------------------------------------------------
  // Test D — Clip Extraction UI (Mode A, Mode B, Mode C)
  // --------------------------------------------------------------------------
  test('Test D — Extraction modal: Mode A (command check, no -y), Mode C checks, Mode B short clip import', async () => {
    // Open extraction modal
    const extractClipBtn = page.locator('[data-testid="extract-clip-btn"]');
    await extractClipBtn.click();

    const modal = page.locator('[data-testid="clip-extraction-modal"]');
    await expect(modal).toBeVisible();

    // --- Mode A: Native FFmpeg Assisting ---
    await expect(page.locator('[data-testid="tab-mode-a"]')).toBeVisible();

    // Verify default PowerShell command
    const commandBox = page.locator('[data-testid="command-preview-box"]');
    await expect(commandBox).toBeVisible();
    let commandText = await commandBox.innerText();

    // Strict safety checks:
    expect(commandText).toContain('ffmpeg');
    expect(commandText).toContain('-ss 00:02:00.000');
    expect(commandText).toContain('-to 00:02:25.000');
    expect(commandText).not.toContain(' -y '); // Silent overwrite omitted
    expect(commandText).toContain('-c:v libx264');

    // Switch to CMD
    await page.locator('[data-testid="shell-cmd-btn"]').click();
    commandText = await commandBox.innerText();
    expect(commandText).toContain('ffmpeg');

    // Switch to Bash
    await page.locator('[data-testid="shell-bash-btn"]').click();
    commandText = await commandBox.innerText();
    expect(commandText).toContain('ffmpeg');

    // Switch to Fast Copy mode
    await page.locator('[data-testid="mode-fast-copy-btn"]').click();
    commandText = await commandBox.innerText();
    expect(commandText).toContain('-c copy');
    const keyframeWarning = page.locator('[data-testid="keyframe-warning-notice"]');
    await expect(keyframeWarning).toBeVisible();
    await expect(keyframeWarning).toContainText('GOP');

    // Switch back to Frame-Accurate
    await page.locator('[data-testid="mode-frame-accurate-btn"]').click();

    // --- Mode C: Browser Capture Experimental Notice ---
    await page.locator('[data-testid="tab-mode-c"]').click();
    const browserCaptureWarning = page.locator('[data-testid="browser-capture-warning"]');
    await expect(browserCaptureWarning).toBeVisible();
    await expect(browserCaptureWarning).toContainText('Experimental Feature Notice');

    // --- Mode B: Import Short Clip ---
    await page.locator('[data-testid="tab-mode-b"]').click();
    const importDropzone = page.locator('[data-testid="import-clip-dropzone"]');
    await expect(importDropzone).toBeVisible();

    // Provide the short clip fixture (336 KB, 25.0s)
    const importInput = page.locator('[data-testid="import-clip-file-input"]');
    await importInput.setInputFiles(CLIP_PATH);

    // Verify duration displays 25.0s
    await expect(page.getByText('Duration: 25.0s')).toBeVisible();

    // Confirm & Stage clip
    const confirmImportBtn = page.locator('[data-testid="confirm-direct-import-btn"]');
    await expect(confirmImportBtn).toBeVisible();
    await confirmImportBtn.click();

    // Modal closes and StagedClipCard appears
    await expect(modal).not.toBeVisible();
    const stagedCard = page.locator('[data-testid="staged-clip-video-player"]');
    await expect(stagedCard).toBeVisible();

    // Verify card metadata: 25.00s, ~328.7 KB (or similar formatted size)
    await expect(page.getByText('Direct File Import')).toBeVisible();
    await expect(page.getByText('25.0s', { exact: false }).first()).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // Test E — Explicit Short-Clip Upload
  // --------------------------------------------------------------------------
  test('Test E — Explicit short-clip upload transmits ONLY 336 KB staged clip and creates temporary session', async () => {
    const uploadBtn = page.locator('[data-testid="upload-to-qwen-btn"]');
    await expect(uploadBtn).toBeVisible();
    await expect(uploadBtn).toBeEnabled();

    // Intercept upload request to assert uploaded bytes
    let uploadMethod = '';
    let uploadUrl = '';

    const [uploadRequest, uploadResponse] = await Promise.all([
      page.waitForRequest((req) => {
        if (req.url().includes('/api/v1/videos/upload-clip') && req.method() === 'POST') {
          uploadMethod = req.method();
          uploadUrl = req.url();
          return true;
        }
        return false;
      }),
      page.waitForResponse((res) => res.url().includes('/api/v1/videos/upload-clip')),
      uploadBtn.click(),
    ]);

    expect(uploadResponse.status()).toBe(201);
    expect(uploadMethod).toBe('POST');
    expect(uploadUrl).toContain('/api/v1/videos/upload-clip');
    expect(uploadRequest.headers()['content-type']).toContain('multipart/form-data');
    const resJson = await uploadResponse.json();

    // Assert video is marked temporary and session credentials created
    expect(resJson.video_id).toBeDefined();
    expect(resJson.is_temporary).toBe(true);
    expect(resJson.session_id).toBeDefined();
    expect(resJson.session_token).toBeDefined();
    expect(resJson.size_bytes).toBe(336619);

    // Determine uploaded size from request headers or body or server response
    const contentLength = parseInt(uploadRequest.headers()['content-length'] || '0', 10);
    const postBuffer = uploadRequest.postDataBuffer();
    const uploadedClipBytes = postBuffer ? postBuffer.length : (contentLength || resJson.size_bytes);

    // CRITICAL PRIVACY ASSERTION:
    // Only the staged short clip was transmitted (~336 KB + multipart headers < 450 KB),
    // NEVER the 1.28 GB original recording!
    expect(uploadedClipBytes).toBeGreaterThan(300_000);
    expect(uploadedClipBytes).toBeLessThan(1_000_000);
    expect(uploadedClipBytes).toBeLessThan(1_323_258_538 * 0.01); // < 1% of original file
  });

  // --------------------------------------------------------------------------
  // Test F — Mock Qwen Video Understanding Result
  // --------------------------------------------------------------------------
  test('Test F — Mock Qwen video understanding completes with amber MOCK banner, timeline, and events', async () => {
    // Wait for the worker to claim and complete the job, and the timeline to appear
    const mockBanner = page.locator('[data-testid="mock-inference-banner"]');
    await expect(mockBanner).toBeVisible({ timeout: 45000 });

    // Assert explicit amber mock disclaimer
    await expect(mockBanner).toContainText('MOCK / TEST DATA — NOT REAL VIDEO ANALYSIS');
    await expect(mockBanner).toContainText('deterministic simulation for development and testing');

    // Assert Mock Engine badge
    const mockBadge = page.locator('[data-testid="mock-inference-badge"]');
    await expect(mockBadge).toBeVisible();
    await expect(mockBadge).toHaveText('Mock Engine');

    // Timeline view displays summary and events
    await expect(page.getByText('Chronological Event Timeline')).toBeVisible();
    await expect(page.getByText('Temporary Clip')).toBeVisible();

    // Verify observable events are listed
    const eventTimeLocators = page.locator('[data-testid="event-clip-time"]');
    const eventCount = await eventTimeLocators.count();
    expect(eventCount).toBeGreaterThan(0);

    // Verify clip-relative timestamps and source timestamps are visible
    const firstSourceTime = page.locator('[data-testid="event-source-time"]').first();
    await expect(firstSourceTime).toBeVisible();
    await expect(firstSourceTime).toContainText('Source:');

    // Summary and individual event copying contain only the requested text.
    // 1. Copy Summary
    const copySummaryBtn = page.locator('[data-testid="copy-summary-btn"]');
    await expect(copySummaryBtn).toBeVisible();
    await copySummaryBtn.click();
    await expect(copySummaryBtn).toContainText('Copied Summary');
    const summaryClipText = await page.evaluate(() => navigator.clipboard.readText());
    expect(summaryClipText.length).toBeGreaterThan(10);

    const eventDescription = await page.locator('[data-testid="event-description-0"]').textContent();
    const copyEventButton = page.locator('[data-testid="copy-event-0"]');
    await copyEventButton.click();
    await expect(copyEventButton).toContainText('Copied');
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(eventDescription);
    await expect(page.getByRole('button', { name: 'Copy Events' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Copy JSON' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Download JSON' })).toHaveCount(0);
  });

  // --------------------------------------------------------------------------
  // Test G - The result navigation exposes exactly the two intended tabs.
  test('Test G - Results show only Video Understanding and Generate Questions', async () => {
    const resultTabs = page.locator('[data-testid="results-tab-navigation"] button');
    await expect(resultTabs).toHaveCount(2);
    await expect(page.locator('[data-testid="grounded-qa-input"]')).toHaveCount(0);
    await expect(page.getByText('Whodunnit Review Workspace')).toHaveCount(0);
    await expect(page.locator('[data-testid="open-whodunnit-export-btn"]')).toHaveCount(0);
  });

  // Test H - Criteria reach the rule-based question generator.
  test('Test H - Criteria shape generated question wording', async () => {
    await page.getByRole('button', { name: 'Generate Questions' }).click();
    const criteria = 'Focus on the kettle. Include timestamps in each question.';
    await page.locator('[data-testid="criteria-textarea"]').fill(criteria);

    const requestPromise = page.waitForRequest((request) =>
      request.url().includes('/jobs/question-generations') && request.method() === 'POST',
    );
    await page.locator('[data-testid="generate-questions-button"]').click();
    const request = await requestPromise;
    expect(JSON.parse(request.postData() || '{}').criteria_text).toBe(criteria);

    await expect(page.locator('[data-testid="question-generation-mode"]')).toHaveText('Rule-based template generation', { timeout: 35000 });
    await expect(page.locator('[data-testid="generated-question-card"]')).toHaveCount(2);
    await expect(page.locator('[data-testid="generated-question-text"]').first()).toContainText('at 00:03.0?');
  });

  // Test I - Edits copy current wording and survive tab navigation.
  test('Test I - Edited question remains available in the current session', async () => {
    const editText = 'Who collects the kettle at 00:03?';
    await page.locator('[data-testid="edit-question-button-0"]').click();
    await page.locator('[data-testid="edit-question-0"]').fill(editText);
    await page.locator('[data-testid="save-question-0"]').click();
    await page.locator('[data-testid="copy-question-button-0"]').click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(editText);

    await page.getByRole('button', { name: 'Video Understanding' }).click();
    await page.getByRole('button', { name: 'Generate Questions' }).click();
    await expect(page.locator('[data-testid="generated-question-text"]').first()).toHaveText(editText);
  });

  // Test J - JSON export and annotation-review controls are absent from results.
  test('Test J - Simplified result controls', async () => {
    await expect(page.getByRole('button', { name: 'Copy JSON' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Download JSON' })).toHaveCount(0);
    await expect(page.locator('[data-testid="download-analysis-json-btn"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="copy-review-json-btn"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="download-review-csv-link"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="accept-event-btn-0"]')).toHaveCount(0);
  });

  // Test K - Temporary analyses still have an explicit retention control.
  test('Test K - Explicit Save to Library marks analysis persistent', async () => {
    await page.getByRole('button', { name: 'Video Understanding' }).click();
    const saveBtn = page.locator('[data-testid="save-analysis-persistent-btn"]');
    if (await saveBtn.isVisible()) {
      await saveBtn.click();
      await expect(page.locator('[data-testid="analysis-persistent-badge"]')).toBeVisible({ timeout: 10000 });
    } else {
      await expect(page.locator('[data-testid="analysis-persistent-badge"]')).toBeVisible();
    }
  });
});
// Test L — Source Switching, Invalidation and State Isolation
// --------------------------------------------------------------------------
test.describe('CASTLE QA Studio — Test L: Source Switching & Lifecycle', () => {
  test('Test L — Switching sources cleans up local state, revokes URLs, prevents stale leaks', async ({ page }) => {
    await page.goto('/');

    // 1. Open local video
    const fileInput = page.locator('[data-testid="local-video-file-input"]');
    await fileInput.setInputFiles(VIDEO_PATH);
    await expect(page.getByText('Local video — Not uploaded').first()).toBeVisible({ timeout: 10000 });

    // 2. Stage a clip
    const extractBtn = page.locator('[data-testid="extract-clip-btn"]');
    await extractBtn.click();
    await page.locator('[data-testid="tab-mode-b"]').click();
    await page.locator('[data-testid="import-clip-file-input"]').setInputFiles(CLIP_PATH);
    await page.locator('[data-testid="confirm-direct-import-btn"]').click();
    await expect(page.locator('[data-testid="staged-clip-video-player"]')).toBeVisible();

    // 3. Clear local video using clear button
    const clearBtn = page.locator('button[title="Clear selected local video"], button[title="Clear selected video"]').first();
    if (await clearBtn.isVisible()) {
      await clearBtn.click();
    }

    // Staged clip card should be destroyed
    await expect(page.locator('[data-testid="staged-clip-video-player"]')).not.toBeVisible();

    // Local video indicator must be gone
    await expect(page.getByText('Local video — Not uploaded')).not.toBeVisible();

    // If video element is still present for a server video, verify its source is not a blob: URL
    const videoElem = page.locator('[data-testid="video-element"]');
    if (await videoElem.isVisible()) {
      const src = await videoElem.getAttribute('src');
      expect(src?.startsWith('blob:')).toBeFalsy();
    }
  });
});
