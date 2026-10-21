import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { App } from '../src/App';
import { ClipSelectionPanel } from '../src/features/videos/ClipSelectionPanel';
import { VideoPlayer } from '../src/features/videos/VideoPlayer';
import {
  formatTimestamp,
  parseTimestamp,
  validateInterval,
  formatDuration,
} from '../src/features/videos/timestampUtils';
import { LocalVideoItem, VideoIntervalSelection } from '../src/shared/types';
import { api } from '../src/shared/api/client';

describe('Task 2: Interactive Video Timestamp Selection & Preview Tests', () => {
  const mockFile = new File(['dummy-video-bytes'], 'security_cam_long.mp4', {
    type: 'video/mp4',
  });

  const mockLocalVideo: LocalVideoItem = {
    sourceType: 'local',
    file: mockFile,
    objectUrl: 'blob:http://localhost:3000/local-uuid-1234',
    filename: 'security_cam_long.mp4',
    sizeBytes: 104857600, // 100 MB
    durationSeconds: 7200, // 2 hours
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // 1. Timestamp formatting and parsing utilities
  describe('Timestamp formatting, parsing, and duration utilities', () => {
    it('formats timestamps into HH:MM:SS.mmm format with subsecond precision', () => {
      expect(formatTimestamp(0)).toBe('00:00:00.000');
      expect(formatTimestamp(1.5)).toBe('00:00:01.500');
      expect(formatTimestamp(75.25)).toBe('00:01:15.250');
      expect(formatTimestamp(3675.123)).toBe('01:01:15.123');
      expect(formatTimestamp(7234.567)).toBe('02:00:34.567');
      expect(formatTimestamp(-10)).toBe('00:00:00.000');
      expect(formatTimestamp(NaN)).toBe('00:00:00.000');
    });

    it('parses diverse timestamp strings into exact seconds with subsecond precision', () => {
      expect(parseTimestamp('00:00:00.000')).toBe(0);
      expect(parseTimestamp('01:01:15.123')).toBe(3675.123);
      expect(parseTimestamp('1:01:15.123')).toBe(3675.123);
      expect(parseTimestamp('01:15.500')).toBe(75.5);
      expect(parseTimestamp('1:15.5')).toBe(75.5);
      expect(parseTimestamp('45.5')).toBe(45.5);
      expect(parseTimestamp('120')).toBe(120);

      // Rejection of malformed or out-of-range timestamps
      expect(parseTimestamp('')).toBeNull();
      expect(parseTimestamp('invalid')).toBeNull();
      expect(parseTimestamp('-5')).toBeNull();
      expect(parseTimestamp('00:65:00')).toBeNull(); // minutes >= 60
      expect(parseTimestamp('00:00:75')).toBeNull(); // seconds >= 60
    });

    it('formats duration into friendly human-readable strings', () => {
      expect(formatDuration(0)).toBe('0.0s');
      expect(formatDuration(15.5)).toBe('15.5s');
      expect(formatDuration(75)).toBe('1m 15.0s');
      expect(formatDuration(3665)).toBe('1h 1m 5.0s');
    });
  });

  // 2. Interval validation
  describe('Interval validation logic', () => {
    it('validates start and end relationships correctly', () => {
      // Valid
      expect(validateInterval(10, 25, 100).isValid).toBe(true);

      // End <= start
      const invalidEnd = validateInterval(25, 10, 100);
      expect(invalidEnd.isValid).toBe(false);
      expect(invalidEnd.error).toContain('strictly greater than start');

      // Equal start and end
      expect(validateInterval(15, 15, 100).isValid).toBe(false);

      // Negative start
      const negativeStart = validateInterval(-1, 10, 100);
      expect(negativeStart.isValid).toBe(false);
      expect(negativeStart.error).toContain('cannot be negative');

      // End exceeds video duration
      const exceedsDuration = validateInterval(10, 120, 60);
      expect(exceedsDuration.isValid).toBe(false);
      expect(exceedsDuration.error).toContain('cannot exceed video duration');

      // Configurable max duration check
      const exceedsMax = validateInterval(0, 120, 300, 60);
      expect(exceedsMax.isValid).toBe(false);
      expect(exceedsMax.error).toContain('exceeds the maximum allowed duration');
    });
  });

  // 3. Marking start and end timestamps
  it('1. Marking start and end timestamps from current video playback position', () => {
    const onJumpTo = vi.fn();
    const onPreview = vi.fn();

    const { rerender } = render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={15.425}
        videoDuration={7200}
        selections={[]}
        activeInterval={null}
        onAddSelection={vi.fn()}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={onPreview}
        onJumpTo={onJumpTo}
        onClearActiveInterval={vi.fn()}
      />
    );

    const markStartBtn = screen.getByTestId('mark-start-btn');
    fireEvent.click(markStartBtn);

    const startInput = screen.getByTestId('start-timestamp-input') as HTMLInputElement;
    expect(startInput.value).toBe('00:00:15.425');

    // Simulate playback advancing to 45.850
    rerender(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={45.85}
        videoDuration={7200}
        selections={[]}
        activeInterval={null}
        onAddSelection={vi.fn()}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={onPreview}
        onJumpTo={onJumpTo}
        onClearActiveInterval={vi.fn()}
      />
    );

    const markEndBtn = screen.getByTestId('mark-end-btn');
    fireEvent.click(markEndBtn);

    const endInput = screen.getByTestId('end-timestamp-input') as HTMLInputElement;
    expect(endInput.value).toBe('00:00:45.850');
  });

  // 4. Manual timestamp input & keyboard accessibility
  it('2. Manual timestamp input synchronizes with calculated duration', () => {
    render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={0}
        videoDuration={7200}
        selections={[]}
        activeInterval={null}
        onAddSelection={vi.fn()}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={vi.fn()}
        onJumpTo={vi.fn()}
        onClearActiveInterval={vi.fn()}
      />
    );

    const startInput = screen.getByTestId('start-timestamp-input');
    const endInput = screen.getByTestId('end-timestamp-input');

    fireEvent.change(startInput, { target: { value: '00:01:20.000' } });
    fireEvent.change(endInput, { target: { value: '00:01:50.000' } });

    // Duration: 30 seconds -> 30.0s
    expect(screen.getByText('Selected Interval: 30.0s')).toBeInTheDocument();
  });

  // 5. Intervals in videos longer than one hour
  it('3. Handles intervals in videos longer than one hour (> 3600 seconds)', () => {
    const onAddSelection = vi.fn();

    render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={4500}
        videoDuration={7200}
        selections={[]}
        activeInterval={null}
        onAddSelection={onAddSelection}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={vi.fn()}
        onJumpTo={vi.fn()}
        onClearActiveInterval={vi.fn()}
      />
    );

    const startInput = screen.getByTestId('start-timestamp-input');
    const endInput = screen.getByTestId('end-timestamp-input');
    const labelInput = screen.getByTestId('selection-label-input');
    const addBtn = screen.getByTestId('add-selection-btn');

    // Interval: 01:15:30.500 (4530.5s) to 01:25:45.000 (5145s)
    fireEvent.change(startInput, { target: { value: '01:15:30.500' } });
    fireEvent.change(endInput, { target: { value: '01:25:45.000' } });
    fireEvent.change(labelInput, { target: { value: 'Suspect exits warehouse' } });

    fireEvent.click(addBtn);

    expect(onAddSelection).toHaveBeenCalledTimes(1);
    const addedSelection: VideoIntervalSelection = onAddSelection.mock.calls[0][0];
    expect(addedSelection.startSeconds).toBe(4530.5);
    expect(addedSelection.endSeconds).toBe(5145);
    expect(addedSelection.durationSeconds).toBe(614.5);
    expect(addedSelection.label).toBe('Suspect exits warehouse');
  });

  // 6. Invalid interval validation messages
  it('4. Rejects invalid interval when end time is before start time or exceeds duration', () => {
    const onAddSelection = vi.fn();

    render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={0}
        videoDuration={60} // 60s total duration
        selections={[]}
        activeInterval={null}
        onAddSelection={onAddSelection}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={vi.fn()}
        onJumpTo={vi.fn()}
        onClearActiveInterval={vi.fn()}
      />
    );

    const startInput = screen.getByTestId('start-timestamp-input');
    const endInput = screen.getByTestId('end-timestamp-input');
    const addBtn = screen.getByTestId('add-selection-btn');

    // Case A: End <= Start
    fireEvent.change(startInput, { target: { value: '00:00:30.000' } });
    fireEvent.change(endInput, { target: { value: '00:00:10.000' } });
    fireEvent.click(addBtn);

    expect(onAddSelection).not.toHaveBeenCalled();
    expect(screen.getByTestId('selection-validation-error')).toHaveTextContent(
      'End timestamp must be strictly greater than start timestamp.'
    );

    // Case B: End exceeds video duration (60s)
    fireEvent.change(startInput, { target: { value: '00:00:10.000' } });
    fireEvent.change(endInput, { target: { value: '00:02:00.000' } });
    fireEvent.click(addBtn);

    expect(onAddSelection).not.toHaveBeenCalled();
    expect(screen.getByTestId('selection-validation-error')).toHaveTextContent(
      'cannot exceed video duration'
    );
  });

  // 7. Previewing selected interval and pausing at end boundary in VideoPlayer
  it('5. Previewing selected interval seeks to start, displays overlay, and pauses at end boundary', async () => {
    const onTimeUpdate = vi.fn();
    const pauseSpy = vi.spyOn(window.HTMLMediaElement.prototype, 'pause');
    vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockResolvedValue();

    await act(async () => {
      render(
        <VideoPlayer
          localVideo={mockLocalVideo}
          activeInterval={{ start: 10, end: 20 }}
          seekRequest={{ time: 10, autoPlay: true, id: 1 }}
          onTimeUpdate={onTimeUpdate}
        />
      );
    });

    const videoEl = screen.getByTestId('video-element') as HTMLVideoElement;

    // Overlay is displayed with Selection Preview text and formatted timestamps
    expect(screen.getByTestId('active-interval-overlay')).toHaveTextContent(
      'Selection Preview: 00:00:10.000 – 00:00:20.000 (10.0s)'
    );

    // Simulate video playing up to the end boundary (20.0s)
    act(() => {
      Object.defineProperty(videoEl, 'currentTime', { value: 20.0, writable: true });
      fireEvent.timeUpdate(videoEl);
    });

    expect(pauseSpy).toHaveBeenCalled();
  });

  // 8. Multiple saved selections management (preview, edit, remove)
  it('6. Supports multiple selections with preview, edit, and removal actions', () => {
    const sel1: VideoIntervalSelection = {
      id: 'sel-1',
      videoRef: 'security_cam_long.mp4-104857600',
      startSeconds: 80,
      endSeconds: 110,
      durationSeconds: 30,
      label: 'Suspect enters front door',
      createdAt: new Date().toISOString(),
    };

    const sel2: VideoIntervalSelection = {
      id: 'sel-2',
      videoRef: 'security_cam_long.mp4-104857600',
      startSeconds: 310,
      endSeconds: 345,
      durationSeconds: 35,
      label: 'Vehicle arrives',
      createdAt: new Date().toISOString(),
    };

    const onPreview = vi.fn();
    const onRemove = vi.fn();
    const onUpdate = vi.fn();

    render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={0}
        videoDuration={7200}
        selections={[sel1, sel2]}
        activeInterval={null}
        onAddSelection={vi.fn()}
        onUpdateSelection={onUpdate}
        onRemoveSelection={onRemove}
        onPreviewInterval={onPreview}
        onJumpTo={vi.fn()}
        onClearActiveInterval={vi.fn()}
      />
    );

    // Both selections are listed
    expect(screen.getByText('Saved Intervals (2)')).toBeInTheDocument();
    expect(screen.getByText(/Selection 1/)).toBeInTheDocument();
    expect(screen.getByText('— Suspect enters front door')).toBeInTheDocument();
    expect(screen.getByText(/Selection 2/)).toBeInTheDocument();
    expect(screen.getByText('— Vehicle arrives')).toBeInTheDocument();

    // Preview Selection 2
    fireEvent.click(screen.getByTestId('preview-selection-sel-2'));
    expect(onPreview).toHaveBeenCalledWith({ start: 310, end: 345 });

    // Remove Selection 1
    fireEvent.click(screen.getByTestId('remove-selection-sel-1'));
    expect(onRemove).toHaveBeenCalledWith('sel-1');

    // Edit Selection 2 loads into editor
    fireEvent.click(screen.getByTestId('edit-selection-sel-2'));
    const startInput = screen.getByTestId('start-timestamp-input') as HTMLInputElement;
    expect(startInput.value).toBe(formatTimestamp(310));
    expect(screen.getByText('Update Selection')).toBeInTheDocument();
  });

  // 9. Interactive range sliders and jump buttons
  it('7. Interactive range sliders and jump buttons operate accurately', () => {
    const onJumpTo = vi.fn();

    render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={50}
        videoDuration={100}
        selections={[]}
        activeInterval={null}
        onAddSelection={vi.fn()}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={vi.fn()}
        onJumpTo={onJumpTo}
        onClearActiveInterval={vi.fn()}
      />
    );

    const startSlider = screen.getByTestId('start-range-slider');
    const endSlider = screen.getByTestId('end-range-slider');

    fireEvent.change(startSlider, { target: { value: '12.5' } });
    fireEvent.change(endSlider, { target: { value: '35.0' } });

    // Jump to Start button invokes onJumpTo with 12.5
    fireEvent.click(screen.getByTestId('jump-to-start-btn'));
    expect(onJumpTo).toHaveBeenCalledWith(12.5, false);

    // Jump to End button invokes onJumpTo with 35.0
    fireEvent.click(screen.getByTestId('jump-to-end-btn'));
    expect(onJumpTo).toHaveBeenCalledWith(35.0, false);
  });

  // 10. Extraction action trigger
  it('8. Triggers clip extraction action with the selected interval', () => {
    const onOpenExtraction = vi.fn();

    render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={0}
        videoDuration={7200}
        selections={[]}
        activeInterval={null}
        onAddSelection={vi.fn()}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={vi.fn()}
        onJumpTo={vi.fn()}
        onClearActiveInterval={vi.fn()}
        onOpenExtraction={onOpenExtraction}
      />
    );

    const extractBtn = screen.getByTestId('extract-clip-btn');
    expect(extractBtn).not.toBeDisabled();

    fireEvent.click(extractBtn);
    expect(onOpenExtraction).toHaveBeenCalledTimes(1);
    expect(onOpenExtraction).toHaveBeenCalledWith(
      expect.objectContaining({
        start: expect.any(Number),
        end: expect.any(Number),
      })
    );
  });

  // 11. Zero backend upload calls during selection or preview
  it('9. Never calls backend upload or inference APIs during selection or preview', () => {
    const uploadSpy = vi.spyOn(api, 'uploadVideo');
    const understandingSpy = vi.spyOn(api, 'submitVideoUnderstanding');
    const qaQuestionSpy = vi.spyOn(api, 'askVideoQuestion');

    const onAdd = vi.fn();
    const onPreview = vi.fn();

    render(
      <ClipSelectionPanel
        localVideo={mockLocalVideo}
        currentTime={30}
        videoDuration={7200}
        selections={[]}
        activeInterval={null}
        onAddSelection={onAdd}
        onUpdateSelection={vi.fn()}
        onRemoveSelection={vi.fn()}
        onPreviewInterval={onPreview}
        onJumpTo={vi.fn()}
        onClearActiveInterval={vi.fn()}
      />
    );

    // Mark start & end
    fireEvent.click(screen.getByTestId('mark-start-btn'));
    fireEvent.click(screen.getByTestId('mark-end-btn'));

    // Manual change
    fireEvent.change(screen.getByTestId('end-timestamp-input'), {
      target: { value: '00:01:00.000' },
    });

    // Preview
    fireEvent.click(screen.getByTestId('preview-selection-btn'));

    // Add selection
    fireEvent.click(screen.getByTestId('add-selection-btn'));

    expect(uploadSpy).not.toHaveBeenCalled();
    expect(understandingSpy).not.toHaveBeenCalled();
    expect(qaQuestionSpy).not.toHaveBeenCalled();
  });

  // 12. Switching between local and server videos preserves selections for local video
  it('10. Switching between local and server videos hides selections on server and restores them on return', async () => {
    vi.spyOn(api, 'getVideos').mockResolvedValue({
      videos: [
        {
          video_id: 'srv_1',
          filename: 'server_clip.mp4',
          duration_seconds: 20,
          size_bytes: 4000000,
        },
      ],
    });
    vi.spyOn(api, 'getAnalysis').mockRejectedValue(new Error('No analysis'));

    let containerEl!: HTMLElement;
    await act(async () => {
      const res = render(<App />);
      containerEl = res.container;
    });

    // Load a local file via hidden input
    const fileInput = containerEl.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [mockFile] } });
    });

    // Panel is now displayed for local video
    expect(screen.getByTestId('clip-selection-panel')).toBeInTheDocument();

    // Add a local selection
    const startInput = screen.getByTestId('start-timestamp-input');
    const endInput = screen.getByTestId('end-timestamp-input');
    const labelInput = screen.getByTestId('selection-label-input');
    const addBtn = screen.getByTestId('add-selection-btn');

    fireEvent.change(startInput, { target: { value: '00:00:05.000' } });
    fireEvent.change(endInput, { target: { value: '00:00:15.000' } });
    fireEvent.change(labelInput, { target: { value: 'Entrance Event' } });
    fireEvent.click(addBtn);

    expect(screen.getByText('— Entrance Event')).toBeInTheDocument();

    // Switch to server video pill
    const serverVideoBtn = screen.getByRole('button', { name: /server_clip\.mp4/i });
    await act(async () => {
      fireEvent.click(serverVideoBtn);
    });

    // Selection panel must NOT be visible when server video is active
    expect(screen.queryByTestId('clip-selection-panel')).not.toBeInTheDocument();

    // Switch back to local video pill
    const localVideoBtn = screen.getByRole('button', { name: /security_cam_long\.mp4/i });
    await act(async () => {
      fireEvent.click(localVideoBtn);
    });

    // Selection panel is visible again, and the saved selection is intact!
    expect(screen.getByTestId('clip-selection-panel')).toBeInTheDocument();
    expect(screen.getByText('— Entrance Event')).toBeInTheDocument();
  });

  // 13. Replacing the local file invalidates its old selections
  it('11. Replacing the local file invalidates its old selections', async () => {
    vi.spyOn(api, 'getVideos').mockResolvedValue({ videos: [] });

    let containerEl!: HTMLElement;
    await act(async () => {
      const res = render(<App />);
      containerEl = res.container;
    });

    const fileInput = containerEl.querySelector('input[type="file"]') as HTMLInputElement;

    // Load File 1
    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [mockFile] } });
    });

    // Add selection to File 1
    const labelInput = screen.getByTestId('selection-label-input');
    const addBtn = screen.getByTestId('add-selection-btn');
    fireEvent.change(labelInput, { target: { value: 'Old File 1 Event' } });
    fireEvent.click(addBtn);

    expect(screen.getByText('— Old File 1 Event')).toBeInTheDocument();

    // Load File 2
    const mockFile2 = new File(['file2-data'], 'another_video.mp4', {
      type: 'video/mp4',
    });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [mockFile2] } });
    });

    // The old selection must NOT be present on the new file!
    expect(screen.queryByText('— Old File 1 Event')).not.toBeInTheDocument();
    expect(screen.getByTestId('no-selections-message')).toBeInTheDocument();
  });
});
