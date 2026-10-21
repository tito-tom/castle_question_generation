import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { GroundedQAPanel } from '../src/features/question-answering/GroundedQAPanel';
import { VideoPlayer } from '../src/features/videos/VideoPlayer';
import { api } from '../src/shared/api/client';
import { VideoQAAnswer, LocalVideoItem, VideoItem } from '../src/shared/types';

describe('Task 1.1: Grounded QA and Video Switching Component Regressions', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Selecting a local video disables server-dependent QA input and Ask button', () => {
    render(
      <GroundedQAPanel
        videoId={null}
        isLocal={true}
        onSeekInterval={vi.fn()}
      />
    );

    const input = screen.getByTestId('grounded-qa-input');
    const askBtn = screen.getByTestId('grounded-qa-ask-btn');
    const notice = screen.getByTestId('local-video-qa-notice');

    expect(input).toBeDisabled();
    expect(askBtn).toBeDisabled();
    expect(notice).toHaveTextContent(
      'Select and extract a short clip before running Qwen or asking questions about this local video.'
    );
  });

  it('2. No QA API call is made when in local video mode, even if input event occurs', async () => {
    const askSpy = vi.spyOn(api, 'askVideoQuestion');

    render(
      <GroundedQAPanel
        videoId={null}
        isLocal={true}
        onSeekInterval={vi.fn()}
      />
    );

    const input = screen.getByTestId('grounded-qa-input');
    fireEvent.change(input, { target: { value: 'Who is in the room?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(askSpy).not.toHaveBeenCalled();
  });

  it('3. Selecting a different video resets stale seek state in VideoPlayer', async () => {
    const videoA: VideoItem = {
      video_id: 'vid_a',
      filename: 'video_a.mp4',
      duration_seconds: 60,
      size_bytes: 1024,
    };

    const videoB: VideoItem = {
      video_id: 'vid_b',
      filename: 'video_b.mp4',
      duration_seconds: 15,
      size_bytes: 1024,
    };

    const onTimeUpdate = vi.fn();

    let rerenderFn!: (ui: React.ReactElement) => void;
    await act(async () => {
      const res = render(
        <VideoPlayer
          video={videoA}
          seekTime={25}
          onTimeUpdate={onTimeUpdate}
        />
      );
      rerenderFn = res.rerender;
    });

    // Now switch to Video B with seekTime reset to null (Issue 2 fix in App.tsx)
    await act(async () => {
      rerenderFn(
        <VideoPlayer
          video={videoB}
          seekTime={null}
          onTimeUpdate={onTimeUpdate}
        />
      );
    });

    // Video B is rendered cleanly with its filename and 00:00.0 time format
    expect(screen.getByText('video_b.mp4')).toBeInTheDocument();
    expect(screen.getByText(/00:00\.0 \/ 00:15\.0/)).toBeInTheDocument();
  });

  it('4. Previous QA answers do not appear when switching to a different video', async () => {
    const mockAnswer: VideoQAAnswer = {
      question: 'Where is the cup?',
      answer: 'The cup is on the table at 00:05.',
      confidence: 0.95,
      is_observable: true,
      start_seconds: 5.0,
      end_seconds: 7.0,
      referenced_events: [0],
    };

    vi.spyOn(api, 'askVideoQuestion').mockResolvedValueOnce(mockAnswer);

    const { rerender } = render(
      <GroundedQAPanel
        videoId="video_server_1"
        isLocal={false}
        onSeekInterval={vi.fn()}
      />
    );

    // Ask a question on video_server_1
    const input = screen.getByTestId('grounded-qa-input');
    const askBtn = screen.getByTestId('grounded-qa-ask-btn');

    fireEvent.change(input, { target: { value: 'Where is the cup?' } });
    fireEvent.click(askBtn);

    // Answer appears for video_server_1
    await waitFor(() => {
      expect(screen.getByText('The cup is on the table at 00:05.')).toBeInTheDocument();
    });

    // Switch to video_server_2
    rerender(
      <GroundedQAPanel
        videoId="video_server_2"
        isLocal={false}
        onSeekInterval={vi.fn()}
      />
    );

    // Previous QA answers must be cleared immediately
    expect(screen.queryByText('The cup is on the table at 00:05.')).not.toBeInTheDocument();
  });

  it('5. An in-flight QA response from Video A cannot populate Video B if switched before response arrives', async () => {
    let resolveVideoA!: (val: VideoQAAnswer) => void;
    const delayedPromiseVideoA = new Promise<VideoQAAnswer>((resolve) => {
      resolveVideoA = resolve;
    });

    vi.spyOn(api, 'askVideoQuestion').mockImplementation((vid) => {
      if (vid === 'video_a') {
        return delayedPromiseVideoA;
      }
      return Promise.resolve({
        question: 'Video B question?',
        answer: 'Video B answer.',
        confidence: 0.9,
        is_observable: true,
        referenced_events: [],
      });
    });

    const { rerender } = render(
      <GroundedQAPanel
        videoId="video_a"
        isLocal={false}
        onSeekInterval={vi.fn()}
      />
    );

    // Submit question for Video A (response will hang)
    const input = screen.getByTestId('grounded-qa-input');
    const askBtn = screen.getByTestId('grounded-qa-ask-btn');
    fireEvent.change(input, { target: { value: 'Stale Question for A' } });
    fireEvent.click(askBtn);

    // User switches to Video B BEFORE Video A's response arrives
    rerender(
      <GroundedQAPanel
        videoId="video_b"
        isLocal={false}
        onSeekInterval={vi.fn()}
      />
    );

    // Now Video A's promise finally resolves
    await act(async () => {
      resolveVideoA({
        question: 'Stale Question for A',
        answer: 'This answer belongs to Video A and must NOT appear on Video B!',
        confidence: 0.99,
        is_observable: true,
        referenced_events: [],
      });
    });

    // Assert Video A's answer was discarded and does NOT populate Video B
    expect(
      screen.queryByText('This answer belongs to Video A and must NOT appear on Video B!')
    ).not.toBeInTheDocument();
  });

  it('6. Switching back to server videos restores valid QA functionality', async () => {
    const mockAnswer: VideoQAAnswer = {
      question: 'Who opened the door?',
      answer: 'Person 1 opened the door.',
      confidence: 0.92,
      is_observable: true,
      referenced_events: [1],
    };

    vi.spyOn(api, 'askVideoQuestion').mockResolvedValueOnce(mockAnswer);

    // Start in local mode
    const { rerender } = render(
      <GroundedQAPanel
        videoId={null}
        isLocal={true}
        onSeekInterval={vi.fn()}
      />
    );

    expect(screen.getByTestId('grounded-qa-input')).toBeDisabled();

    // Switch to server video
    rerender(
      <GroundedQAPanel
        videoId="server_restored_vid"
        isLocal={false}
        onSeekInterval={vi.fn()}
      />
    );

    const input = screen.getByTestId('grounded-qa-input');
    const askBtn = screen.getByTestId('grounded-qa-ask-btn');

    expect(input).not.toBeDisabled();

    fireEvent.change(input, { target: { value: 'Who opened the door?' } });
    fireEvent.click(askBtn);

    await waitFor(() => {
      expect(screen.getByText('Person 1 opened the door.')).toBeInTheDocument();
    });
  });

  it('7. Existing local object URL behavior and rendering remains intact', () => {
    const mockFile = new File(['fake-mp4-data'], 'local_kitchen.mp4', {
      type: 'video/mp4',
    });

    const localItem: LocalVideoItem = {
      sourceType: 'local',
      file: mockFile,
      objectUrl: 'blob:http://localhost:3000/mock-uuid-test',
      filename: 'local_kitchen.mp4',
      sizeBytes: 15728640, // 15.0 MB
      durationSeconds: 42,
    };

    render(
      <VideoPlayer
        localVideo={localItem}
        onReplaceVideo={vi.fn()}
        onClearVideo={vi.fn()}
      />
    );

    // Player displays the local badge, filename, and formatted size
    expect(screen.getByText('Local video — Not uploaded')).toBeInTheDocument();
    expect(screen.getByText('local_kitchen.mp4')).toBeInTheDocument();
    expect(screen.getByText(/\(15(\.0)? MB\)/)).toBeInTheDocument();
    expect(screen.getByTitle('Replace current video')).toBeInTheDocument();
    expect(screen.getByTitle('Clear selected video')).toBeInTheDocument();
  });
});
