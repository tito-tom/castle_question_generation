import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { QuestionGenerationWorkspace } from '../src/features/question-generation/QuestionGenerationWorkspace';
import { readCriteriaFile } from '../src/features/question-generation/criteriaFiles';
import { QuestionGenerationResponse, VideoAnalysis } from '../src/shared/types';

const analysis: VideoAnalysis = {
  analysis_id: 'analysis_for_questions',
  clip_name: 'clip.mp4',
  model_name: 'mock',
  summary: 'A person handles a red door.',
  events: [],
};

const generation: QuestionGenerationResponse = {
  generation_id: 'gen_0123456789abcdef0123456789abcdef',
  analysis_id: analysis.analysis_id,
  generator: 'template',
  question_count: 1,
  is_persistent: false,
  questions: [{
    question: 'Who opens the red door?',
    answer: null,
    actor_reference: 'person_2',
    source_event_index: 3,
    evidence: { clip_name: 'clip.mp4', start_seconds: 4, end_seconds: 8 },
    generation_method: 'template',
    review_status: 'pending',
  }],
};

describe('QuestionGenerationWorkspace', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it('imports local Markdown criteria and sends the reviewed text to generation', async () => {
    const onGenerate = vi.fn().mockResolvedValue(generation);
    render(<QuestionGenerationWorkspace analysis={analysis} isGenerating={false} onGenerate={onGenerate} />);

    const file = new File(['Focus on the red door and keep questions concise.'], 'guide.md', { type: 'text/markdown' });
    fireEvent.change(screen.getByTestId('criteria-file-input'), { target: { files: [file] } });

    const criteriaInput = screen.getByTestId('criteria-textarea') as HTMLTextAreaElement;
    await waitFor(() => expect(criteriaInput.value).toContain('Focus on the red door'));
    fireEvent.click(screen.getByTestId('generate-questions-button'));

    await waitFor(() => expect(onGenerate).toHaveBeenCalledWith('Focus on the red door and keep questions concise.'));
    expect(screen.getByTestId('question-generation-mode')).toHaveTextContent('Rule-based template generation');
    expect(screen.getByText('Who opens the red door?')).toBeInTheDocument();
    expect(screen.getByTestId('generated-question-card')).toHaveAttribute('data-source-event-index', '3');
  });

  it('allows editing and copies only the current question text', async () => {
    const onGenerate = vi.fn().mockResolvedValue(generation);
    render(<QuestionGenerationWorkspace analysis={analysis} isGenerating={false} onGenerate={onGenerate} />);
    fireEvent.click(screen.getByTestId('generate-questions-button'));
    await screen.findByText('Who opens the red door?');

    fireEvent.click(screen.getByTestId('edit-question-button-0'));
    fireEvent.change(screen.getByTestId('edit-question-0'), { target: { value: 'Who opens the red door at 00:04?' } });
    fireEvent.click(screen.getByTestId('save-question-0'));
    expect(screen.getByTestId('generated-question-text')).toHaveTextContent('Who opens the red door at 00:04?');

    fireEvent.click(screen.getByTestId('copy-question-button-0'));
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Who opens the red door at 00:04?'));
  });

  it('clears criteria without discarding the current generated questions', async () => {
    const onGenerate = vi.fn().mockResolvedValue(generation);
    render(<QuestionGenerationWorkspace analysis={analysis} isGenerating={false} onGenerate={onGenerate} />);
    fireEvent.change(screen.getByTestId('criteria-textarea'), { target: { value: 'Focus on the door.' } });
    fireEvent.click(screen.getByTestId('generate-questions-button'));
    await screen.findByText('Who opens the red door?');

    fireEvent.click(screen.getByTestId('clear-criteria-button'));
    expect((screen.getByTestId('criteria-textarea') as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByText('Who opens the red door?')).toBeInTheDocument();
  });
});

describe('criteria file reader', () => {
  it('extracts text values from JSON without executing or retaining the file', async () => {
    const file = new File([JSON.stringify({ criteria: 'Focus on actions', style: ['Use concise wording'] })], 'criteria.json');
    await expect(readCriteriaFile(file)).resolves.toContain('criteria: Focus on actions');
    await expect(readCriteriaFile(file)).resolves.toContain('style: Use concise wording');
  });

  it('rejects unsupported formats and files larger than 16 KB', async () => {
    await expect(readCriteriaFile(new File(['x'], 'criteria.pdf'))).rejects.toThrow('.txt, .md, or .json');
    await expect(readCriteriaFile(new File(['x'.repeat(16 * 1024 + 1)], 'criteria.txt'))).rejects.toThrow('16 KB');
  });
});
