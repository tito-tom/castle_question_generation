import { describe, expect, it } from 'vitest';
import { createAnalysisWindows, formatWindowOutputName, getRetryableWindowIds } from '../src/features/videos/analysisWindows';
import { generateNativeBatchCommand } from '../src/features/videos/nativeCommandGenerator';

describe('long interval analysis windows', () => {
  it('splits multi-minute intervals into sequential 90s windows with 10s overlap', () => {
    expect(createAnalysisWindows(120, 300)).toEqual([
      { index: 1, startSeconds: 120, endSeconds: 210 },
      { index: 2, startSeconds: 200, endSeconds: 290 },
      { index: 3, startSeconds: 280, endSeconds: 300 },
    ]);
  });

  it('supports intervals up to ten minutes and rejects longer selections', () => {
    expect(createAnalysisWindows(0, 600)).toHaveLength(8);
    expect(() => createAnalysisWindows(0, 600.1)).toThrow('at most 10 minutes');
  });

  it('retries only incomplete windows and keeps completed analysis IDs', () => {
    expect(getRetryableWindowIds(
      [{ id: 'window-1' }, { id: 'window-2' }, { id: 'window-3' }],
      { 'window-1': 'clip_batch_window_1' },
    )).toEqual(['window-2', 'window-3']);
  });

  it('names clips with stable window indexes for provenance-safe import', () => {
    const windows = createAnalysisWindows(300, 400);
    expect(formatWindowOutputName('Kitchen 8.mp4', windows[0])).toMatch(/_w01_00-05-00_to_00-06-30\.mp4$/);
  });

  it('generates a native batch script for every window without uploading the source', () => {
    const windows = createAnalysisWindows(0, 170);
    const outputs = windows.map((window) => formatWindowOutputName('source.mp4', window));
    const generated = generateNativeBatchCommand('powershell', {
      sourceFilename: 'source.mp4',
      sourcePathPlaceholder: 'source.mp4',
      windows,
      outputFilenames: outputs,
      mode: 'frame_accurate',
    });
    expect(generated.outputFilenames).toHaveLength(2);
    expect(generated.scriptContent).toContain('ffmpeg -ss 00:00:00.000 -to 00:01:30.000');
    expect(generated.scriptContent).toContain('ffmpeg -ss 00:01:20.000 -to 00:02:50.000');
    expect(generated.scriptContent).toContain('only imported window clips are uploaded');
  });

  it('keeps an untrusted source filename from adding executable lines to the batch script', () => {
    const windows = createAnalysisWindows(0, 90);
    const generated = generateNativeBatchCommand('powershell', {
      sourceFilename: 'kitchen.mp4\nWrite-Output injected',
      sourcePathPlaceholder: 'kitchen.mp4',
      windows,
      outputFilenames: windows.map((window) => formatWindowOutputName('kitchen.mp4', window)),
      mode: 'frame_accurate',
    });
    expect(generated.scriptContent).not.toContain('Write-Output injected');
    expect(generated.scriptContent).toContain('# Source: kitchen.mp4');
  });
});
