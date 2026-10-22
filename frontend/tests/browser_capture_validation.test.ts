import { describe, expect, it, vi, afterEach } from 'vitest';
import { getPreferredMimeType, validateVideoFile } from '../src/features/videos/browserCaptureExtractor';

describe('browser capture media validation', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('selects a recorder-supported container instead of assuming MP4', () => {
    vi.stubGlobal('MediaRecorder', {
      isTypeSupported: (type: string) => type.startsWith('video/webm'),
    });
    expect(getPreferredMimeType()).toMatch(/^video\/webm/);
  });

  it('rejects empty and non-video output before staging', async () => {
    await expect(validateVideoFile(new File([], 'empty.webm', { type: 'video/webm' })))
      .rejects.toThrow(/empty/i);
    await expect(validateVideoFile(new File(['bytes'], 'bad.txt', { type: 'text/plain' })))
      .rejects.toThrow(/unsupported/i);
  });
});
