import React, { useState, useEffect, useRef } from 'react';
import {
  HelpCircle,
  Send,
  CheckCircle2,
  AlertTriangle,
  Play,
  HardDrive,
  Info,
  Copy,
  Check,
  Download,
  Sparkles,
} from 'lucide-react';
import { api } from '../../shared/api/client';
import { VideoQAAnswer } from '../../shared/types';

interface GroundedQAPanelProps {
  videoId: string | null;
  analysisId?: string | null;
  isLocal?: boolean;
  onSeekInterval: (interval: { start: number; end: number }) => void;
  onGenerateQuestions?: () => void;
  isGeneratingQuestions?: boolean;
}

export const GroundedQAPanel: React.FC<GroundedQAPanelProps> = ({
  videoId,
  analysisId,
  isLocal = false,
  onSeekInterval,
  onGenerateQuestions,
  isGeneratingQuestions = false,
}) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [answers, setAnswers] = useState<VideoQAAnswer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  // Active target reference to prevent stale in-flight async responses from repopulating another video
  const activeTargetRef = useRef({ videoId, analysisId });
  activeTargetRef.current = { videoId, analysisId };
  const currentRequestIdRef = useRef(0);

  // Reset component state and invalidate in-flight requests whenever video or analysis changes
  useEffect(() => {
    currentRequestIdRef.current += 1;
    setAnswers([]);
    setError(null);
    setQuestion('');
    setLoading(false);
  }, [videoId, analysisId]);

  const suggestedQuestions = [
    'Who was the first person to interact with an object?',
    'Did anyone pick up or move an item?',
    'What action occurred at the beginning?',
    'When did someone leave or enter?',
  ];

  const canAsk = Boolean(videoId || analysisId) && !isLocal;

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q || !canAsk) return;

    const thisRequestId = ++currentRequestIdRef.current;
    const targetVideoId = videoId;
    const targetAnalysisId = analysisId;

    setLoading(true);
    setError(null);

    try {
      let res: VideoQAAnswer;
      if (targetVideoId) {
        res = await api.askVideoQuestion(targetVideoId, q, targetAnalysisId || undefined);
      } else if (targetAnalysisId) {
        res = await api.askAnalysisQuestion(targetAnalysisId, q);
      } else {
        throw new Error('No target video or analysis provided');
      }

      // Verify this response is still for the currently active target and request
      if (
        thisRequestId === currentRequestIdRef.current &&
        activeTargetRef.current.videoId === targetVideoId &&
        activeTargetRef.current.analysisId === targetAnalysisId
      ) {
        setAnswers((prev) => [res, ...prev]);
        if (!queryText) setQuestion('');
      }
    } catch (err: unknown) {
      if (
        thisRequestId === currentRequestIdRef.current &&
        activeTargetRef.current.videoId === targetVideoId
      ) {
        setError(err instanceof Error ? err.message : 'Question answering failed');
      }
    } finally {
      if (thisRequestId === currentRequestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  const handleCopyAnswer = (ans: VideoQAAnswer, idx: number) => {
    const intervalStr =
      ans.start_seconds !== null && ans.start_seconds !== undefined && ans.end_seconds !== null && ans.end_seconds !== undefined
        ? `\nEvidence interval: ${formatSeconds(ans.start_seconds)} - ${formatSeconds(ans.end_seconds)}`
        : '';
    const statusStr = ans.is_human_reviewed
      ? 'Human-Reviewed Annotation'
      : ans.is_observable && ans.confidence > 0
      ? 'Evidence-Supported Candidate (Model-Generated)'
      : 'Uncertain / Unsupported (Model-Generated)';
    const text = `Q: ${ans.question}\nA: ${ans.answer}${intervalStr}\nStatus: ${statusStr}\nHeuristic Score: ${ans.confidence.toFixed(2)} (evidence-matching heuristic, not calibrated probability)`;
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx((prev) => (prev === idx ? null : prev)), 2000);
  };

  const handleCopyAllQA = () => {
    if (answers.length === 0) return;
    const text = answers
      .map((ans, i) => {
        const intervalStr =
          ans.start_seconds !== null && ans.start_seconds !== undefined && ans.end_seconds !== null && ans.end_seconds !== undefined
            ? ` (${formatSeconds(ans.start_seconds)} - ${formatSeconds(ans.end_seconds)})`
            : '';
        return `[${i + 1}] Q: ${ans.question}\nA: ${ans.answer}${intervalStr}`;
      })
      .join('\n\n');
    navigator.clipboard.writeText(text);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  const handleDownloadQAJson = () => {
    if (answers.length === 0) return;
    const blob = new Blob([JSON.stringify(answers, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `grounded_qa_${videoId || analysisId || 'export'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
            <HelpCircle className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Grounded Video QA</h2>
            <p className="text-[11px] text-slate-400">
              Ask questions grounded strictly in observable video evidence and timestamps
            </p>
          </div>
        </div>

        {onGenerateQuestions && (
          <button
            onClick={onGenerateQuestions}
            disabled={isGeneratingQuestions || !canAsk}
            data-testid="trigger-generate-questions-btn"
            className="flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium px-3 py-1.5 rounded-lg transition shadow"
            title="Generate QA candidates automatically with Qwen"
          >
            {isGeneratingQuestions ? (
              <>
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Generating QA...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Generate Questions</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Local Video Informational Notice */}
      {isLocal && (
        <div
          data-testid="local-video-qa-notice"
          className="bg-amber-950/30 border border-amber-800/40 rounded-lg p-3 text-xs text-amber-200/90 flex items-start space-x-2.5"
        >
          <HardDrive className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-medium text-amber-300">Local Video Mode</p>
            <p className="text-[11px] text-amber-200/80 leading-relaxed">
              Select and extract a short clip before running Qwen or asking questions about this local video.
            </p>
          </div>
        </div>
      )}

      {/* No Server Video Selected Notice */}
      {!isLocal && !videoId && !analysisId && (
        <div
          data-testid="no-video-qa-notice"
          className="bg-slate-950/40 border border-slate-800 rounded-lg p-3 text-xs text-slate-400 flex items-center space-x-2"
        >
          <Info className="w-4 h-4 text-slate-500 shrink-0" />
          <span>Select an uploaded server video or extract a local clip to ask grounded questions.</span>
        </div>
      )}

      {/* Suggested prompts */}
      <div className="flex flex-wrap gap-1.5">
        {suggestedQuestions.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleAsk(s)}
            disabled={loading || !canAsk}
            className="text-[11px] bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white px-2.5 py-1 rounded-md border border-slate-700/60 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input box */}
      <div className="flex items-center space-x-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
          placeholder={
            isLocal
              ? 'Extract a clip to enable Qwen question answering...'
              : !videoId && !analysisId
              ? 'Select a video to enable question answering...'
              : 'Ask anything about what happens in the video...'
          }
          disabled={loading || !canAsk}
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="grounded-qa-input"
        />

        <button
          onClick={() => handleAsk()}
          disabled={loading || !question.trim() || !canAsk}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium px-4 py-2 rounded-lg transition flex items-center space-x-1.5 shadow"
          data-testid="grounded-qa-ask-btn"
        >
          {loading ? (
            <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              <span>Ask</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/40 p-2.5 rounded-lg">
          {error}
        </div>
      )}

      {/* Answers list & toolbar */}
      {answers.length > 0 && (
        <div className="flex items-center justify-between border-t border-slate-800/60 pt-2 text-xs text-slate-400">
          <span className="font-mono text-[11px]">{answers.length} Q&A answered</span>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopyAllQA}
              data-testid="copy-all-qa-btn"
              className="flex items-center space-x-1 text-[11px] text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2 py-0.5 rounded transition border border-slate-700"
            >
              {copiedAll ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-400" />}
              <span>{copiedAll ? 'Copied All' : 'Copy All Q&A'}</span>
            </button>
            <button
              onClick={handleDownloadQAJson}
              data-testid="download-qa-json-btn"
              className="flex items-center space-x-1 text-[11px] text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-2 py-0.5 rounded transition border border-slate-700"
            >
              <Download className="w-3 h-3 text-slate-400" />
              <span>Download JSON</span>
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
        {answers.map((ans, idx) => (
          <div
            key={idx}
            className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 space-y-2 text-xs"
            data-testid="grounded-qa-answer-item"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-300">{ans.question}</span>

              <div className="flex items-center space-x-1.5 flex-wrap">
                {ans.is_mock ? (
                  <span
                    data-testid="qa-mock-badge"
                    className="text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/40 px-1.5 py-0.5 rounded font-mono"
                    title="Answer derived from simulated test data"
                  >
                    Mock Output
                  </span>
                ) : ans.mock_notice ? (
                  <span
                    data-testid="qa-legacy-badge"
                    className="text-[10px] text-slate-300 bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded font-mono"
                    title="Answer derived from unverified legacy analysis"
                  >
                    Legacy Unverified
                  </span>
                ) : null}
                {ans.is_human_reviewed ? (
                  <span
                    data-testid="qa-status-badge"
                    className="flex items-center space-x-1 text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-full"
                  >
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    <span>Human-Reviewed</span>
                  </span>
                ) : ans.is_observable && ans.confidence > 0 ? (
                  <>
                    <span
                      data-testid="qa-source-badge"
                      className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700"
                    >
                      Model-Generated
                    </span>
                    <span
                      data-testid="qa-status-badge"
                      className="flex items-center space-x-1 text-[10px] text-indigo-400 bg-indigo-950/40 border border-indigo-800/40 px-2 py-0.5 rounded-full"
                    >
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      <span>Evidence-Supported Candidate</span>
                    </span>
                    <span
                      data-testid="qa-confidence-badge"
                      className="text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800 font-mono"
                      title="Heuristic evidence match score (not a calibrated probability)"
                    >
                      Score: {ans.confidence.toFixed(2)}
                    </span>
                  </>
                ) : (
                  <>
                    <span
                      data-testid="qa-source-badge"
                      className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700"
                    >
                      Model-Generated
                    </span>
                    <span
                      data-testid="qa-status-badge"
                      className="flex items-center space-x-1 text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded-full"
                    >
                      <AlertTriangle className="w-2.5 h-2.5" />
                      <span>Uncertain / Unsupported</span>
                    </span>
                  </>
                )}

                <button
                  onClick={() => handleCopyAnswer(ans, idx)}
                  data-testid={`copy-answer-btn-${idx}`}
                  className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
                  title="Copy this answer"
                >
                  {copiedIdx === idx ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>
            </div>

            <p className="text-slate-100 font-medium leading-relaxed bg-slate-900/60 p-2 rounded border border-slate-800/60">
              {ans.answer}
            </p>

            {ans.uncertainty_notes && (
              <p className="text-[11px] text-amber-300/80 bg-amber-950/30 p-2 rounded border border-amber-900/40">
                Note: {ans.uncertainty_notes}
              </p>
            )}

            {ans.start_seconds !== null &&
              ans.start_seconds !== undefined &&
              ans.end_seconds !== null &&
              ans.end_seconds !== undefined && (
                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[11px]">
                  <div className="text-slate-400 truncate max-w-xs">
                    Evidence: {ans.evidence_reasoning || 'Observable action in interval'}
                  </div>

                  <button
                    onClick={() =>
                      onSeekInterval({
                        start: ans.start_seconds!,
                        end: ans.end_seconds!,
                      })
                    }
                    className="flex items-center space-x-1 font-mono text-indigo-400 hover:text-indigo-300 bg-indigo-950/60 hover:bg-indigo-900/60 border border-indigo-800/50 px-2 py-0.5 rounded transition"
                  >
                    <Play className="w-2.5 h-2.5" />
                    <span>
                      {formatSeconds(ans.start_seconds)} - {formatSeconds(ans.end_seconds)}
                    </span>
                  </button>
                </div>
              )}
          </div>
        ))}
      </div>
    </div>
  );
};
