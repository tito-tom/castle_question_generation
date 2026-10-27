import React, { useEffect, useRef, useState } from 'react';
import { Check, Copy, FileUp, Pencil, Sparkles, Trash2 } from 'lucide-react';
import { GeneratedQuestion, QuestionGenerationResponse, VideoAnalysis } from '../../shared/types';
import { MAX_CRITERIA_CHARACTERS, readCriteriaFile } from './criteriaFiles';

interface QuestionDraft extends GeneratedQuestion {
  editedQuestion: string;
}

interface QuestionGenerationWorkspaceProps {
  analysis: VideoAnalysis | null;
  isGenerating: boolean;
  onGenerate: (criteriaText: string) => Promise<QuestionGenerationResponse>;
}

export const QuestionGenerationWorkspace: React.FC<QuestionGenerationWorkspaceProps> = ({
  analysis,
  isGenerating,
  onGenerate,
}) => {
  const [criteriaText, setCriteriaText] = useState('');
  const [criteriaError, setCriteriaError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generation, setGeneration] = useState<QuestionGenerationResponse | null>(null);
  const [questions, setQuestions] = useState<QuestionDraft[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const criteriaFileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setCriteriaText('');
    setCriteriaError(null);
    setGenerationError(null);
    setGeneration(null);
    setQuestions([]);
    setEditingIndex(null);
    if (criteriaFileRef.current) criteriaFileRef.current.value = '';
  }, [analysis?.analysis_id]);

  const handleImportCriteria = async (file?: File) => {
    if (!file) return;
    setCriteriaError(null);
    try {
      const extracted = await readCriteriaFile(file);
      setCriteriaText(extracted);
    } catch (error) {
      setCriteriaError(error instanceof Error ? error.message : 'Could not read criteria file.');
    } finally {
      if (criteriaFileRef.current) criteriaFileRef.current.value = '';
    }
  };

  const handleGenerate = async () => {
    if (!analysis || isGenerating) return;
    setGenerationError(null);
    setGeneration(null);
    setQuestions([]);
    setEditingIndex(null);
    setCopiedIndex(null);
    try {
      const result = await onGenerate(criteriaText);
      setGeneration(result);
      setQuestions(result.questions.map((question) => ({
        ...question,
        editedQuestion: question.question,
      })));
      setEditingIndex(null);
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : 'Question generation failed.');
    }
  };

  const handleCopyQuestion = async (index: number) => {
    try {
      await navigator.clipboard.writeText(questions[index].editedQuestion);
      setCopiedIndex(index);
      window.setTimeout(() => setCopiedIndex((current) => current === index ? null : current), 1800);
    } catch {
      setGenerationError('Clipboard access is unavailable in this browser.');
    }
  };

  const startEditing = (index: number) => {
    setEditingIndex(index);
    setEditText(questions[index].editedQuestion);
  };

  const saveEdit = (index: number) => {
    const nextText = editText.trim();
    if (!nextText) return;
    setQuestions((current) => current.map((question, questionIndex) =>
      questionIndex === index ? { ...question, editedQuestion: nextText } : question,
    ));
    setEditingIndex(null);
  };

  const generatorLabel = generation?.generator === 'template'
    ? 'Rule-based template generation'
    : generation?.generator === 'qwen_local'
      ? 'LLM generation · Qwen local'
      : generation?.generator || 'Question generation';

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4" aria-label="Generate Questions workspace">
      <header>
        <h2 className="text-sm font-semibold text-white">Question Generation</h2>
        <p className="text-xs text-slate-400 mt-1">
          Questions are based on retained video-understanding events. Criteria guide question style and event selection; they do not add video facts.
        </p>
      </header>

      <section className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 space-y-2" aria-labelledby="criteria-heading">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 id="criteria-heading" className="text-xs font-semibold text-slate-200">Question Criteria <span className="font-normal text-slate-500">(optional)</span></h3>
            <p className="text-[11px] text-slate-500 mt-1">Paste preferences or import a small text, Markdown, or JSON file. File contents stay in this browser until you generate.</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <label className="cursor-pointer inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-[11px] text-slate-200 hover:bg-slate-700">
              <FileUp className="w-3.5 h-3.5" /> Import file
              <input
                ref={criteriaFileRef}
                type="file"
                accept=".txt,.md,.json,text/plain,text/markdown,application/json"
                className="sr-only"
                data-testid="criteria-file-input"
                onChange={(event) => void handleImportCriteria(event.currentTarget.files?.[0])}
              />
            </label>
            <button
              type="button"
              onClick={() => { setCriteriaText(''); setCriteriaError(null); }}
              disabled={!criteriaText && !criteriaError}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-[11px] text-slate-400 hover:text-white disabled:opacity-40"
              data-testid="clear-criteria-button"
            >
              <Trash2 className="w-3 h-3" /> Clear
            </button>
          </div>
        </div>
        <textarea
          value={criteriaText}
          onChange={(event) => setCriteriaText(event.target.value.slice(0, MAX_CRITERIA_CHARACTERS))}
          maxLength={MAX_CRITERIA_CHARACTERS}
          rows={5}
          placeholder="Example: Prefer questions about object interactions. Keep wording concise."
          aria-label="Question criteria text"
          data-testid="criteria-textarea"
          className="w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none"
        />
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Criteria are treated as untrusted guidance.</span>
          <span>{criteriaText.length.toLocaleString()} / {MAX_CRITERIA_CHARACTERS.toLocaleString()}</span>
        </div>
        {criteriaError && <p role="alert" className="text-xs text-rose-300">{criteriaError}</p>}
      </section>

      {!analysis && (
        <p className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-400">
          Run video understanding first. Questions can only use its retained event evidence.
        </p>
      )}

      <button
        type="button"
        onClick={() => void handleGenerate()}
        disabled={!analysis || isGenerating}
        data-testid="generate-questions-button"
        className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isGenerating ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
        {isGenerating ? 'Generating Questions…' : 'Generate Questions'}
      </button>

      {generationError && <p role="alert" className="text-xs text-rose-300">{generationError}</p>}

      {generation && (
        <section className="space-y-3" aria-label="Generated questions">
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-3">
            <h3 className="text-xs font-semibold text-white">Generated Questions <span className="text-slate-500 font-normal">({questions.length})</span></h3>
            <span data-testid="question-generation-mode" className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-[10px] text-slate-300">{generatorLabel}</span>
          </div>
          {questions.length === 0 ? (
            <p className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-400">No questions matched the retained event evidence and criteria.</p>
          ) : questions.map((question, index) => (
            <article
              key={`${generation.generation_id ?? generation.analysis_id}-${index}`}
              data-testid="generated-question-card"
              data-source-event-index={question.source_event_index}
              className="rounded-lg border border-slate-800 bg-slate-950/60 p-3"
            >
              {editingIndex === index ? (
                <div className="space-y-2">
                  <textarea
                    autoFocus
                    value={editText}
                    onChange={(event) => setEditText(event.target.value)}
                    aria-label={`Edit question ${index + 1}`}
                    data-testid={`edit-question-${index}`}
                    rows={3}
                    className="w-full resize-y rounded-md border border-indigo-700 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none"
                  />
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={() => setEditingIndex(null)} className="rounded px-2.5 py-1.5 text-xs text-slate-400 hover:text-white">Cancel</button>
                    <button type="button" onClick={() => saveEdit(index)} disabled={!editText.trim()} data-testid={`save-question-${index}`} className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50">Save edit</button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium leading-relaxed text-white" data-testid="generated-question-text">{question.editedQuestion}</p>
                  <div className="flex shrink-0 items-center gap-1">
                    <button type="button" onClick={() => startEditing(index)} data-testid={`edit-question-button-${index}`} className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1.5 text-[11px] text-slate-300 hover:border-indigo-500 hover:text-white">
                      <Pencil className="w-3 h-3" /> Edit
                    </button>
                    <button type="button" onClick={() => void handleCopyQuestion(index)} data-testid={`copy-question-button-${index}`} className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1.5 text-[11px] text-slate-300 hover:border-indigo-500 hover:text-white">
                      {copiedIndex === index ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      {copiedIndex === index ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                </div>
              )}
            </article>
          ))}
        </section>
      )}
    </section>
  );
};
