import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TimelineView } from '../src/features/video-understanding/TimelineView';
import { GroundedQAPanel } from '../src/features/question-answering/GroundedQAPanel';
import { AnnotationReviewWorkspace } from '../src/features/annotations/AnnotationReviewWorkspace';
import { WhodunnitExportModal } from '../src/features/annotations/WhodunnitExportModal';
import { api } from '../src/shared/api/client';
import {
  AnnotationReviewSession,
  VideoAnalysis,
  VideoQAAnswer,
} from '../src/shared/types';

describe('Task 5: Video Understanding, QA, Review and Export Test Suite', () => {
  const sampleAnalysis: VideoAnalysis = {
    analysis_id: 'clip_kitchen_001_analysis',
    clip_name: 'clip_kitchen_001.mp4',
    model_name: 'Qwen/Qwen2.5-VL-7B-Instruct',
    scene: 'Kitchen',
    participants: ['person_1', 'person_2'],
    objects: ['plate', 'cup', 'knife'],
    summary: 'Person 1 takes a cup from the counter and places a plate on the table.',
    source_video_name: 'kitchen_8_day_1.mp4',
    source_start_seconds: 120.0,
    source_end_seconds: 145.0,
    temporal_alignment_status: 'verified',
    is_temporary: true,
    is_persistent: false,
    events: [
      {
        start_seconds: 2.0,
        end_seconds: 6.5,
        clip_start_seconds: 2.0,
        clip_end_seconds: 6.5,
        source_start_seconds: 122.0,
        source_end_seconds: 126.5,
        time_offset_uncertainty: 0.0,
        description: 'Person 1 picks up a white ceramic cup from the counter.',
        actor: 'person_1',
        action: 'picks up',
        object: 'cup',
        object_name: 'cup',
        target: 'counter',
        confidence: 0.95,
      },
      {
        start_seconds: 7.0,
        end_seconds: 12.0,
        clip_start_seconds: 7.0,
        clip_end_seconds: 12.0,
        source_start_seconds: 127.0,
        source_end_seconds: 132.0,
        time_offset_uncertainty: 0.5,
        description: 'Person 2 enters the kitchen and speaks to Person 1.',
        actor: 'person_2',
        action: 'enters',
        object: null,
        object_name: null,
        target: 'kitchen',
        confidence: 0.88,
      },
    ],
  };

  const sampleReviewSession: AnnotationReviewSession = {
    review_id: 'rev_test_5001',
    analysis_id: 'clip_kitchen_001_analysis',
    video_id: 'clip_kitchen_001',
    generation_id: 'gen_init_100',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    reviewer_id: 'annotator_1',
    overall_status: 'in_progress',
    summary: 'Person 1 takes a cup from the counter and places a plate on the table.',
    is_persistent: false,
    events: [
      {
        event_index: 0,
        original_start_seconds: 2.0,
        original_end_seconds: 6.5,
        original_description: 'Person 1 picks up a white ceramic cup from the counter.',
        original_actor: 'person_1',
        original_action: 'picks up',
        original_object: 'cup',
        status: 'pending',
      },
      {
        event_index: 1,
        original_start_seconds: 7.0,
        original_end_seconds: 12.0,
        original_description: 'Person 2 enters the kitchen and speaks to Person 1.',
        original_actor: 'person_2',
        original_action: 'enters',
        status: 'pending',
      },
    ],
    questions: [
      {
        question_index: 0,
        original_question: 'Who picked up the white ceramic cup?',
        original_answer: 'person_1',
        actor_reference: 'person_1',
        source_event_index: 0,
        evidence_start_seconds: 2.0,
        evidence_end_seconds: 6.5,
        status: 'pending',
      },
    ],
  };

  beforeEach(() => {
    vi.restoreAllMocks();

    // Mock clipboard
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      writable: true,
      configurable: true,
    });

    // Mock URL object
    global.URL.createObjectURL = vi.fn().mockReturnValue('blob:http://localhost:3000/mock-download');
    global.URL.revokeObjectURL = vi.fn();
  });

  // =========================================================================
  // Section 1: Video Understanding Workspace & Copy/Download Actions
  // =========================================================================
  describe('1. Video Understanding Workspace & Copy/Download Actions', () => {
    it('renders summary, scene badge, participants, objects and dual-timestamp events', () => {
      render(
        <TimelineView
          analysis={sampleAnalysis}
          currentTime={0}
          onSelectInterval={vi.fn()}
        />
      );

      // Summary and scene
      expect(
        screen.getByText('Person 1 takes a cup from the counter and places a plate on the table.')
      ).toBeInTheDocument();
      expect(screen.getByText('Kitchen')).toBeInTheDocument();

      // Participants & Objects
      expect(screen.getAllByText('person_1').length).toBeGreaterThan(0);
      expect(screen.getAllByText('person_2').length).toBeGreaterThan(0);
      expect(screen.getByText('plate')).toBeInTheDocument();
      expect(screen.getAllByText('cup').length).toBeGreaterThan(0);

      // Event descriptions
      expect(screen.getByText('Person 1 picks up a white ceramic cup from the counter.')).toBeInTheDocument();
      expect(screen.getByText('Person 2 enters the kitchen and speaks to Person 1.')).toBeInTheDocument();

      // Uncertainty badge for event 2
      expect(screen.getByTestId('event-uncertainty-badge')).toHaveTextContent('±0.50s offset');
    });

    it('copies summary to clipboard on click', async () => {
      render(
        <TimelineView
          analysis={sampleAnalysis}
          currentTime={0}
          onSelectInterval={vi.fn()}
        />
      );

      const copySummaryBtn = screen.getByTestId('copy-summary-btn');
      fireEvent.click(copySummaryBtn);

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(sampleAnalysis.summary);
      await waitFor(() => {
        expect(screen.getByText('Copied Summary')).toBeInTheDocument();
      });
    });

    it('copies formatted events list to clipboard on click', async () => {
      render(
        <TimelineView
          analysis={sampleAnalysis}
          currentTime={0}
          onSelectInterval={vi.fn()}
        />
      );

      const copyEventsBtn = screen.getByTestId('copy-events-btn');
      fireEvent.click(copyEventsBtn);

      expect(navigator.clipboard.writeText).toHaveBeenCalled();
      const calledText = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
      expect(calledText).toContain('[Event 1]');
      expect(calledText).toContain('Person 1 picks up a white ceramic cup');
      expect(calledText).toContain('Actor: person_1');
    });

    it('copies full analysis JSON and triggers JSON download', async () => {
      render(
        <TimelineView
          analysis={sampleAnalysis}
          currentTime={0}
          onSelectInterval={vi.fn()}
        />
      );

      // Copy JSON
      const copyJsonBtn = screen.getByTestId('copy-analysis-json-btn');
      fireEvent.click(copyJsonBtn);
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        JSON.stringify(sampleAnalysis, null, 2)
      );

      // Download JSON
      const downloadBtn = screen.getByTestId('download-analysis-json-btn');
      fireEvent.click(downloadBtn);
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('allows explicit saving to persistent storage for temporary analyses', async () => {
      const mockSave = vi.spyOn(api, 'saveAnalysisPersistent').mockResolvedValue({
        ...sampleAnalysis,
        is_persistent: true,
      });

      const onUpdated = vi.fn();
      render(
        <TimelineView
          analysis={sampleAnalysis}
          currentTime={0}
          onSelectInterval={vi.fn()}
          onAnalysisUpdated={onUpdated}
        />
      );

      const saveBtn = screen.getByTestId('save-analysis-persistent-btn');
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(mockSave).toHaveBeenCalledWith('clip_kitchen_001_analysis');
        expect(onUpdated).toHaveBeenCalled();
        expect(screen.getByTestId('analysis-persistent-badge')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // Section 2: Grounded Video QA (Mode A) on Staged Clips & Server Videos
  // =========================================================================
  describe('2. Grounded Video QA (Mode A)', () => {
    it('disables asking and displays informative notice when local video has not yet staged an analyzed clip', () => {
      render(
        <GroundedQAPanel
          videoId={null}
          analysisId={null}
          isLocal={true}
          onSeekInterval={vi.fn()}
        />
      );

      expect(screen.getByTestId('local-video-qa-notice')).toBeInTheDocument();
      expect(screen.getByTestId('grounded-qa-input')).toBeDisabled();
      expect(screen.getByTestId('grounded-qa-ask-btn')).toBeDisabled();
    });

    it('enables question asking once a staged clip is uploaded and analyzed', async () => {
      const mockAnswer: VideoQAAnswer = {
        question: 'Who picked up the cup?',
        answer: 'Person 1 picked up the cup from the kitchen counter.',
        confidence: 0.96,
        is_observable: true,
        start_seconds: 2.0,
        end_seconds: 6.5,
        evidence_reasoning: 'Person 1 interacts with the cup on counter',
        referenced_events: [0],
        video_id: 'clip_kitchen_001',
        analysis_id: 'clip_kitchen_001_analysis',
      };

      const mockAsk = vi.spyOn(api, 'askVideoQuestion').mockResolvedValue(mockAnswer);

      render(
        <GroundedQAPanel
          videoId="clip_kitchen_001"
          analysisId="clip_kitchen_001_analysis"
          isLocal={false}
          onSeekInterval={vi.fn()}
        />
      );

      const input = screen.getByTestId('grounded-qa-input');
      expect(input).not.toBeDisabled();

      fireEvent.change(input, { target: { value: 'Who picked up the cup?' } });
      const askBtn = screen.getByTestId('grounded-qa-ask-btn');
      fireEvent.click(askBtn);

      await waitFor(() => {
        expect(mockAsk).toHaveBeenCalledWith(
          'clip_kitchen_001',
          'Who picked up the cup?',
          'clip_kitchen_001_analysis'
        );
        expect(
          screen.getByText('Person 1 picked up the cup from the kitchen counter.')
        ).toBeInTheDocument();
        expect(screen.getByText('Evidence-Supported Candidate')).toBeInTheDocument();
        expect(screen.getByText('Model-Generated')).toBeInTheDocument();
        expect(screen.getByText('Score: 0.96')).toBeInTheDocument();
      });
    });

    it('supports copying individual answer and copying all Q&A history', async () => {
      const mockAnswer: VideoQAAnswer = {
        question: 'What object was moved?',
        answer: 'A white ceramic cup was moved.',
        confidence: 0.92,
        is_observable: true,
        start_seconds: 2.0,
        end_seconds: 6.5,
        referenced_events: [0],
      };

      vi.spyOn(api, 'askVideoQuestion').mockResolvedValue(mockAnswer);

      render(
        <GroundedQAPanel
          videoId="clip_kitchen_001"
          analysisId="clip_kitchen_001_analysis"
          isLocal={false}
          onSeekInterval={vi.fn()}
        />
      );

      const input = screen.getByTestId('grounded-qa-input');
      fireEvent.change(input, { target: { value: 'What object was moved?' } });
      fireEvent.click(screen.getByTestId('grounded-qa-ask-btn'));

      await waitFor(() => {
        expect(screen.getByText('A white ceramic cup was moved.')).toBeInTheDocument();
      });

      // Copy single answer
      const copyAnswerBtn = screen.getByTestId('copy-answer-btn-0');
      fireEvent.click(copyAnswerBtn);
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
      const singleText = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
      expect(singleText).toContain('Q: What object was moved?');
      expect(singleText).toContain('A: A white ceramic cup was moved.');

      // Copy all Q&A
      const copyAllBtn = screen.getByTestId('copy-all-qa-btn');
      fireEvent.click(copyAllBtn);
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
    });

    it('triggers question generation callback when requested from QA panel', () => {
      const onGen = vi.fn();
      render(
        <GroundedQAPanel
          videoId="clip_kitchen_001"
          analysisId="clip_kitchen_001_analysis"
          isLocal={false}
          onSeekInterval={vi.fn()}
          onGenerateQuestions={onGen}
        />
      );

      const genBtn = screen.getByTestId('trigger-generate-questions-btn');
      fireEvent.click(genBtn);
      expect(onGen).toHaveBeenCalled();
    });
  });

  // =========================================================================
  // Section 3: Annotation Review Workspace & Whodunnit Questions
  // =========================================================================
  describe('3. Annotation Review Workspace', () => {
    it('renders event list and allows accepting, rejecting, and editing items', async () => {
      const mockUpdateEvent = vi.spyOn(api, 'updateEventReview').mockResolvedValue({
        ...sampleReviewSession,
        events: [
          { ...sampleReviewSession.events[0], status: 'accepted' },
          sampleReviewSession.events[1],
        ],
      });

      const onSessionUpdated = vi.fn();
      render(
        <AnnotationReviewWorkspace
          session={sampleReviewSession}
          onSessionUpdated={onSessionUpdated}
          onOpenExportModal={vi.fn()}
          onSeekInterval={vi.fn()}
        />
      );

      // Accept event 0
      const acceptBtn = screen.getByTestId('accept-event-btn-0');
      fireEvent.click(acceptBtn);

      await waitFor(() => {
        expect(mockUpdateEvent).toHaveBeenCalledWith(
          'rev_test_5001',
          0,
          expect.objectContaining({ status: 'accepted' })
        );
        expect(onSessionUpdated).toHaveBeenCalled();
      });
    });

    it('renders generated questions tab and allows human verification', async () => {
      const mockUpdateQuestion = vi.spyOn(api, 'updateQuestionReview').mockResolvedValue({
        ...sampleReviewSession,
        questions: [{ ...sampleReviewSession.questions[0], status: 'accepted' }],
      });

      const onSessionUpdated = vi.fn();
      render(
        <AnnotationReviewWorkspace
          session={sampleReviewSession}
          onSessionUpdated={onSessionUpdated}
          onOpenExportModal={vi.fn()}
          onSeekInterval={vi.fn()}
        />
      );

      // Switch to Questions tab
      fireEvent.click(screen.getByTestId('review-tab-questions'));

      expect(screen.getByText('Who picked up the white ceramic cup?')).toBeInTheDocument();

      // Accept question
      const acceptQBtn = screen.getByTestId('accept-question-btn-0');
      fireEvent.click(acceptQBtn);

      await waitFor(() => {
        expect(mockUpdateQuestion).toHaveBeenCalledWith(
          'rev_test_5001',
          0,
          expect.objectContaining({ status: 'accepted' })
        );
      });
    });

    it('shows sync banner when newer question generation exists and syncs on click', async () => {
      const mockSync = vi.spyOn(api, 'syncReviewSessionQuestions').mockResolvedValue({
        ...sampleReviewSession,
        generation_id: 'gen_new_200',
        questions: [
          sampleReviewSession.questions[0],
          {
            question_index: 1,
            original_question: 'When did Person 2 enter?',
            original_answer: 'person_2',
            status: 'pending',
          },
        ],
      });

      const onSessionUpdated = vi.fn();
      render(
        <AnnotationReviewWorkspace
          session={sampleReviewSession}
          onSessionUpdated={onSessionUpdated}
          onOpenExportModal={vi.fn()}
          onSeekInterval={vi.fn()}
          latestGenerationId="gen_new_200"
        />
      );

      expect(screen.getByTestId('sync-questions-alert')).toBeInTheDocument();
      const syncBtn = screen.getByRole('button', { name: /Sync Questions/i });
      fireEvent.click(syncBtn);

      await waitFor(() => {
        expect(mockSync).toHaveBeenCalledWith('rev_test_5001', 'gen_new_200');
        expect(onSessionUpdated).toHaveBeenCalled();
      });
    });

    it('copies review JSON and supports explicit save to library', async () => {
      const mockSave = vi.spyOn(api, 'saveReviewSessionPersistent').mockResolvedValue({
        ...sampleReviewSession,
        is_persistent: true,
      });

      const onSessionUpdated = vi.fn();
      render(
        <AnnotationReviewWorkspace
          session={sampleReviewSession}
          onSessionUpdated={onSessionUpdated}
          onOpenExportModal={vi.fn()}
          onSeekInterval={vi.fn()}
        />
      );

      // Copy JSON
      fireEvent.click(screen.getByTestId('copy-review-json-btn'));
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        JSON.stringify(sampleReviewSession, null, 2)
      );

      // Download JSON
      fireEvent.click(screen.getByTestId('download-review-json-btn'));
      expect(global.URL.createObjectURL).toHaveBeenCalled();

      // Save to library
      fireEvent.click(screen.getByTestId('save-review-persistent-btn'));
      await waitFor(() => {
        expect(mockSave).toHaveBeenCalledWith('rev_test_5001');
        expect(onSessionUpdated).toHaveBeenCalled();
      });
    });
  });

  // =========================================================================
  // Section 4: Whodunnit Export Modal
  // =========================================================================
  describe('4. Whodunnit Export Modal', () => {
    it('fetches and previews export package, allowing copy and download', async () => {
      const mockPackage = {
        metadata: { profile: 'whodunnit_v1_draft', schema_version: '1.0.0' },
        events: [{ annotation_id: 'evt_0_123', actor: 'person_1', human_verified: true }],
        whodunnit_questions: [{ qa_id: 'qa_0_456', question: 'Who took the cup?', human_verified: true }],
      };

      global.fetch = vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue(mockPackage),
      });

      render(
        <WhodunnitExportModal
          isOpen={true}
          onClose={vi.fn()}
          reviewId="rev_test_5001"
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/"profile": "whodunnit_v1_draft"/)).toBeInTheDocument();
      });

      // Copy package
      const copyBtn = screen.getByRole('button', { name: /Copy/i });
      fireEvent.click(copyBtn);
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        JSON.stringify(mockPackage, null, 2)
      );

      // Download JSON package
      const downloadBtn = screen.getByRole('button', { name: /Download JSON Package/i });
      fireEvent.click(downloadBtn);
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  // =========================================================================
  describe('5. Task 5.1 Verification: Terminology and Video Expiration', () => {
    it('displays uncertain/unsupported badge and model-generated indicator', async () => {
      const mockUnsupported: VideoQAAnswer = {
        question: 'Who juggled apples?',
        answer: 'Based on observable video evidence, this activity does not appear in the video.',
        confidence: 0.0,
        confidence_type: 'heuristic_score',
        is_human_reviewed: false,
        is_observable: false,
        referenced_events: [],
      };

      vi.spyOn(api, 'askVideoQuestion').mockResolvedValue(mockUnsupported);

      render(
        <GroundedQAPanel
          videoId="clip_kitchen_001"
          analysisId="clip_kitchen_001_analysis"
          isLocal={false}
          onSeekInterval={vi.fn()}
        />
      );

      const input = screen.getByTestId('grounded-qa-input');
      fireEvent.change(input, { target: { value: 'Who juggled apples?' } });
      fireEvent.click(screen.getByTestId('grounded-qa-ask-btn'));

      await waitFor(() => {
        expect(screen.getByText('Uncertain / Unsupported')).toBeInTheDocument();
        expect(screen.getByText('Model-Generated')).toBeInTheDocument();
      });
    });

    it('displays original clip expired notice in TimelineView when video_available is false', () => {
      const expiredAnalysis: VideoAnalysis = {
        ...sampleAnalysis,
        video_available: false,
      };

      render(
        <TimelineView
          analysis={expiredAnalysis}
          currentTime={0}
          onSelectInterval={vi.fn()}
        />
      );

      expect(screen.getByTestId('analysis-video-unavailable-badge')).toBeInTheDocument();
      expect(screen.getByText(/Original clip expired \(results preserved\)/)).toBeInTheDocument();
    });

    it('displays original clip expired notice in AnnotationReviewWorkspace when video_available is false', () => {
      const expiredSession: AnnotationReviewSession = {
        ...sampleReviewSession,
        video_available: false,
      };

      render(
        <AnnotationReviewWorkspace
          session={expiredSession}
          onSessionUpdated={vi.fn()}
          onOpenExportModal={vi.fn()}
          onSeekInterval={vi.fn()}
        />
      );

      expect(screen.getByTestId('review-video-unavailable-badge')).toBeInTheDocument();
      expect(screen.getByText(/Original clip expired \(results preserved\)/)).toBeInTheDocument();
    });
  });

});
