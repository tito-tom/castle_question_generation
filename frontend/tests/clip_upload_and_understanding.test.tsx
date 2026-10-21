import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { StagedClipCard } from '../src/features/videos/StagedClipCard';
import { TimelineView } from '../src/features/video-understanding/TimelineView';
import { App } from '../src/App';
import { api } from '../src/shared/api/client';
import { StagedClipItem, VideoAnalysis, VideoItem } from '../src/shared/types';

describe('Task 4: Temporary Clip Upload and Qwen Understanding Test Suite', () => {
  const dummyFile = new File(['short clip data'], 'clip_test.mp4', { type: 'video/mp4' });

  const validStagedClip: StagedClipItem = {
    id: 'clip_stage_1',
    file: dummyFile,
    objectUrl: 'blob:http://localhost:3000/mock-staged-clip',
    filename: 'clip_test.mp4',
    sizeBytes: 5 * 1024 * 1024, // 5 MB (well under 200MB)
    durationSeconds: 15.0, // 15s (well under 120s)
    method: 'native_ffmpeg_assisted',
    alignmentStatus: 'verified',
    userConfirmedAssociation: true,
    sourceVideoName: 'kitchen_8_day_1.mp4',
    sourceVideoRef: 'src_instance_test',
    sourceStartSeconds: 100.0,
    sourceEndSeconds: 115.0,
    sourceDurationSeconds: 15.0,
    durationDeltaSeconds: 0.0,
    createdAt: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // Section 1: StagedClipCard Limits, State Transitions, and Retry
  // =========================================================================
  describe('1. StagedClipCard Client-Side Limits and States', () => {
    it('disables Analyze button and displays warning if clip size exceeds 200 MB', () => {
      const oversizedClip: StagedClipItem = {
        ...validStagedClip,
        sizeBytes: 205 * 1024 * 1024, // 205 MB
      };

      const onAnalyze = vi.fn();
      render(
        <StagedClipCard
          stagedClip={oversizedClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
          onAnalyzeClip={onAnalyze}
        />
      );

      const btn = screen.getByTestId('upload-to-qwen-btn');
      expect(btn).toBeDisabled();

      const warning = screen.getByTestId('clip-limit-warning');
      expect(warning).toBeInTheDocument();
      expect(warning).toHaveTextContent('exceeds 200 MB maximum upload limit');

      fireEvent.click(btn);
      expect(onAnalyze).not.toHaveBeenCalled();
    });

    it('disables Analyze button and displays warning if clip duration exceeds 120 seconds', () => {
      const longClip: StagedClipItem = {
        ...validStagedClip,
        durationSeconds: 135.5, // 135.5s
      };

      const onAnalyze = vi.fn();
      render(
        <StagedClipCard
          stagedClip={longClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
          onAnalyzeClip={onAnalyze}
        />
      );

      const btn = screen.getByTestId('upload-to-qwen-btn');
      expect(btn).toBeDisabled();

      const warning = screen.getByTestId('clip-limit-warning');
      expect(warning).toBeInTheDocument();
      expect(warning).toHaveTextContent('exceeds 120s maximum limit');

      fireEvent.click(btn);
      expect(onAnalyze).not.toHaveBeenCalled();
    });

    it('enables button for valid clip and fires onAnalyzeClip on click', () => {
      const onAnalyze = vi.fn();
      render(
        <StagedClipCard
          stagedClip={validStagedClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
          onAnalyzeClip={onAnalyze}
        />
      );

      const btn = screen.getByTestId('upload-to-qwen-btn');
      expect(btn).not.toBeDisabled();
      expect(btn).toHaveTextContent('Analyze Clip with Qwen');

      fireEvent.click(btn);
      expect(onAnalyze).toHaveBeenCalledWith(validStagedClip);
    });

    it('displays upload progress bar when uploading to server', () => {
      render(
        <StagedClipCard
          stagedClip={validStagedClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
          isAnalyzing={true}
          uploadProgress={45}
        />
      );

      const btn = screen.getByTestId('upload-to-qwen-btn');
      expect(btn).toBeDisabled();
      expect(btn).toHaveTextContent('Uploading clip 45%...');
      expect(screen.getByText('Uploading clip to server...')).toBeInTheDocument();
      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('displays analysis progress spinner and status when Qwen job is running', () => {
      render(
        <StagedClipCard
          stagedClip={validStagedClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
          isAnalyzing={true}
          uploadProgress={null}
          analysisProgressText="Qwen analyzing clip..."
        />
      );

      const btn = screen.getByTestId('upload-to-qwen-btn');
      expect(btn).toBeDisabled();
      expect(btn).toHaveTextContent('Qwen analyzing clip...');
    });

    it('displays error banner and retry button on failure', () => {
      const onRetry = vi.fn();
      render(
        <StagedClipCard
          stagedClip={validStagedClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
          analysisError="Network timeout while uploading clip"
          onRetryAnalysis={onRetry}
        />
      );

      const errorBox = screen.getByTestId('clip-analysis-error');
      expect(errorBox).toBeInTheDocument();
      expect(errorBox).toHaveTextContent('Network timeout while uploading clip');

      const retryBtn = screen.getByText('Retry');
      fireEvent.click(retryBtn);
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  // =========================================================================
  // Section 2: TimelineView Source Mapping and Uncertainty Rendering
  // =========================================================================
  describe('2. TimelineView Temporal Display and Uncertainty Indicators', () => {
    const mockAnalysis: VideoAnalysis = {
      analysis_id: 'an_test_clip_1',
      clip_name: 'clip_fridge.mp4',
      model_name: 'Qwen/Qwen2.5-VL-7B-Instruct',
      summary: 'A person opens the refrigerator, inspects a bottle, and sets it on the table.',
      scene: 'Kitchen counter and refrigerator',
      participants: ['Person 1', 'Suspect'],
      objects: ['Refrigerator', 'Milk bottle', 'Counter'],
      source_video_name: 'kitchen_8_day_1.mp4',
      source_start_seconds: 120.0,
      source_end_seconds: 135.0,
      temporal_alignment_status: 'verified',
      is_temporary: true,
      events: [
        {
          start_seconds: 2.5,
          end_seconds: 7.0,
          clip_start_seconds: 2.5,
          clip_end_seconds: 7.0,
          source_start_seconds: 122.5,
          source_end_seconds: 127.0,
          time_offset_uncertainty: 0.12, // 0.12s uncertainty
          description: 'Suspect reaches towards the refrigerator door handle.',
          actor: 'Suspect',
          action: 'reach',
          object: 'refrigerator door',
          confidence: 0.94,
        },
        {
          start_seconds: 8.0,
          end_seconds: 13.5,
          clip_start_seconds: 8.0,
          clip_end_seconds: 13.5,
          source_start_seconds: 128.0,
          source_end_seconds: 133.5,
          time_offset_uncertainty: 0.0, // verified zero uncertainty
          description: 'Suspect removes the glass bottle from the top shelf.',
          actor: 'Suspect',
          action: 'remove',
          object: 'glass bottle',
          confidence: 0.98,
        },
      ],
    };

    it('renders clip timestamps, mapped source timestamps, and uncertainty badges', () => {
      const onSelect = vi.fn();
      render(
        <TimelineView
          analysis={mockAnalysis}
          currentTime={125.0}
          onSelectInterval={onSelect}
        />
      );

      // Header checks
      expect(screen.getByText('Chronological Event Timeline')).toBeInTheDocument();
      expect(screen.getByText('Temporary Clip')).toBeInTheDocument();
      expect(screen.getByText(/Source: kitchen_8_day_1.mp4/)).toBeInTheDocument();
      expect(screen.getByText('Person 1')).toBeInTheDocument();
      expect(screen.getByText('Milk bottle')).toBeInTheDocument();

      // Timestamps checks
      const clipTimes = screen.getAllByTestId('event-clip-time');
      expect(clipTimes).toHaveLength(2);
      expect(clipTimes[0]).toHaveTextContent('00:02.5 - 00:07.0');

      const sourceTimes = screen.getAllByTestId('event-source-time');
      expect(sourceTimes).toHaveLength(2);
      expect(sourceTimes[0]).toHaveTextContent('Source: 02:02.5 - 02:07.0');

      // Uncertainty badge should only appear for event 0 (offset 0.12s)
      const uncertaintyBadges = screen.getAllByTestId('event-uncertainty-badge');
      expect(uncertaintyBadges).toHaveLength(1);
      expect(uncertaintyBadges[0]).toHaveTextContent('±0.12s offset');

      // Clicking Play in source seeks to source interval in the long video
      const playBtn = screen.getByTestId('play-event-interval-0');
      expect(playBtn).toHaveTextContent('Play in source');
      fireEvent.click(playBtn);

      expect(onSelect).toHaveBeenCalledWith({
        start: 122.5,
        end: 127.0,
      });
    });
  });

  // =========================================================================
  // Section 3: End-to-End Clip Upload & Qwen Analysis Workflow
  // =========================================================================
  describe('3. End-to-End Workflow & Zero Original Video Upload Enforcement', () => {
    it('uploads ONLY staged clip file (not the 1.28 GB local video) and loads Qwen analysis into Timeline', async () => {
      // 1. Mock API responses
      const serverVideos: VideoItem[] = [
        {
          video_id: 'vid_server_sample',
          filename: 'sample_server.mp4',
          duration_seconds: 45.0,
          size_bytes: 5000000,
        },
      ];

      vi.spyOn(api, 'getVideos').mockResolvedValue({
        videos: serverVideos,
        total: 1,
      });

      const uploadTemporarySpy = vi.spyOn(api, 'uploadTemporaryClip').mockResolvedValue({
        video_id: 'clip_uploaded_uuid_123',
        filename: 'clip1.mp4',
        duration_seconds: 15.0,
        size_bytes: 3000,
        is_temporary: true,
      });

      const submitJobSpy = vi.spyOn(api, 'submitVideoUnderstanding').mockResolvedValue({
        job_id: 'job_understand_456',
        status: 'queued',
      });

      const pollJobSpy = vi.spyOn(api, 'pollJobUntilFinished').mockResolvedValue({
        job_id: 'job_understand_456',
        job_type: 'video_understanding',
        status: 'completed',
        result_id: 'an_qwen_789',
        created_at: new Date().toISOString(),
      });

      const mockLoadedAnalysis: VideoAnalysis = {
        analysis_id: 'an_qwen_789',
        clip_name: 'clip1.mp4',
        model_name: 'Qwen/Qwen2.5-VL-7B-Instruct',
        summary: 'Qwen video understanding output for staged clip.',
        scene: 'Surveillance scene',
        participants: ['Suspect'],
        objects: ['Door'],
        source_video_name: 'kitchen_8_day_1.mp4',
        source_start_seconds: 72.5,
        source_end_seconds: 87.5,
        temporal_alignment_status: 'verified',
        is_temporary: true,
        events: [
          {
            start_seconds: 0.0,
            end_seconds: 10.0,
            clip_start_seconds: 0.0,
            clip_end_seconds: 10.0,
            source_start_seconds: 72.5,
            source_end_seconds: 82.5,
            description: 'Subject enters through door.',
          },
        ],
      };

      vi.spyOn(api, 'getAnalysis').mockResolvedValue(mockLoadedAnalysis);
      vi.spyOn(api, 'createOrLoadReviewSession').mockResolvedValue({
        review_id: 'rev_123',
        analysis_id: 'an_qwen_789',
        video_id: 'clip_uploaded_uuid_123',
        status: 'in_progress',
        events: [],
        questions: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      // 2. Render App
      let containerEl!: HTMLElement;
      await act(async () => {
        const res = render(<App />);
        containerEl = res.container;
      });

      // 3. Open local video (1.28 GB)
      const bigLocalFile = new File(['1.28 GB dummy content'], 'kitchen_8_day_1.mp4', {
        type: 'video/mp4',
      });
      Object.defineProperty(bigLocalFile, 'size', { value: 1323258538 }); // 1.28 GB

      const fileInput = containerEl.querySelector('input[type="file"]') as HTMLInputElement;
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [bigLocalFile] } });
      });

      // 4. Open extraction modal and stage a clip
      fireEvent.click(screen.getByTestId('extract-clip-btn'));
      fireEvent.click(screen.getByTestId('tab-mode-b'));

      const dropzoneInput = screen
        .getByTestId('import-clip-dropzone')
        .querySelector('input[type="file"]') as HTMLInputElement;
      const smallClipFile = new File(['short clip data'], 'extracted_clip.mp4', {
        type: 'video/mp4',
      });

      await act(async () => {
        fireEvent.change(dropzoneInput, { target: { files: [smallClipFile] } });
      });

      fireEvent.click(screen.getByTestId('confirm-direct-import-btn'));

      // Staged clip card is now present
      expect(screen.getByTestId('staged-clip-card')).toBeInTheDocument();

      // 5. Click "Analyze Clip with Qwen"
      const analyzeBtn = screen.getByTestId('upload-to-qwen-btn');
      expect(analyzeBtn).not.toBeDisabled();

      await act(async () => {
        fireEvent.click(analyzeBtn);
      });

      // 6. Verify uploadTemporaryClip was called with the short clip, NOT the big local file!
      expect(uploadTemporarySpy).toHaveBeenCalledTimes(1);
      const [uploadedFile, metadata] = uploadTemporarySpy.mock.calls[0];
      expect(uploadedFile).toBe(smallClipFile);
      expect(uploadedFile).not.toBe(bigLocalFile);
      expect(metadata?.sourceFilename).toBe('kitchen_8_day_1.mp4');

      // 7. Verify job submission & polling
      expect(submitJobSpy).toHaveBeenCalledWith('clip_uploaded_uuid_123', 2.0);
      expect(pollJobSpy).toHaveBeenCalledWith('job_understand_456');

      // 8. Verify UI switched to Timeline and displays loaded analysis
      await waitFor(() => {
        expect(screen.getByText('Qwen video understanding output for staged clip.')).toBeInTheDocument();
      });

      expect(screen.getByText('Subject enters through door.')).toBeInTheDocument();
    });

    it('cancels ongoing clip job polling if user switches to a server video', async () => {
      // Setup server videos
      const serverVideo: VideoItem = {
        video_id: 'vid_server_alpha',
        filename: 'server_alpha.mp4',
        duration_seconds: 60.0,
        size_bytes: 4000000,
      };

      vi.spyOn(api, 'getVideos').mockResolvedValue({
        videos: [serverVideo],
        total: 1,
      });

      // Upload succeeds, but polling takes time (hanging promise)
      vi.spyOn(api, 'uploadTemporaryClip').mockResolvedValue({
        video_id: 'clip_slow_poll',
        filename: 'slow.mp4',
        duration_seconds: 10.0,
        size_bytes: 2000,
        is_temporary: true,
      });

      vi.spyOn(api, 'submitVideoUnderstanding').mockResolvedValue({
        job_id: 'job_slow_789',
        status: 'queued',
      });

      let resolvePoll!: (val: any) => void;
      const hangingPoll = new Promise((resolve) => {
        resolvePoll = resolve;
      });
      vi.spyOn(api, 'pollJobUntilFinished').mockReturnValue(hangingPoll as any);

      const getAnalysisSpy = vi.spyOn(api, 'getAnalysis').mockImplementation(async (id: string) => {
        if (id === 'stale_analysis_id') {
          return {
            analysis_id: 'stale_analysis_id',
            clip_name: 'slow.mp4',
            model_name: 'Qwen',
            summary: 'Stale analysis should never appear',
            events: [],
          };
        }
        throw new Error('Analysis not found');
      });

      // Render App
      let containerEl!: HTMLElement;
      await act(async () => {
        const res = render(<App />);
        containerEl = res.container;
      });

      // Open local file & stage clip
      const localFile = new File(['dummy'], 'local_kitchen.mp4', { type: 'video/mp4' });
      const fileInput = containerEl.querySelector('input[type="file"]') as HTMLInputElement;
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [localFile] } });
      });

      fireEvent.click(screen.getByTestId('extract-clip-btn'));
      fireEvent.click(screen.getByTestId('tab-mode-b'));
      const dropzoneInput = screen
        .getByTestId('import-clip-dropzone')
        .querySelector('input[type="file"]') as HTMLInputElement;
      const smallClip = new File(['clip'], 'small.mp4', { type: 'video/mp4' });
      await act(async () => {
        fireEvent.change(dropzoneInput, { target: { files: [smallClip] } });
      });
      fireEvent.click(screen.getByTestId('confirm-direct-import-btn'));

      // Start analyzing
      await act(async () => {
        fireEvent.click(screen.getByTestId('upload-to-qwen-btn'));
      });

      // Now user clicks on server video pill while poll is pending!
      const serverPill = screen.getByText('server_alpha.mp4');
      await act(async () => {
        fireEvent.click(serverPill);
      });

      // Now resolve the hanging poll
      await act(async () => {
        resolvePoll({
          job_id: 'job_slow_789',
          job_type: 'video_understanding',
          status: 'completed',
          result_id: 'stale_analysis_id',
        });
      });

      // Stale analysis must not have been loaded or displayed
      expect(screen.queryByText('Stale analysis should never appear')).not.toBeInTheDocument();
    });
  });
});
