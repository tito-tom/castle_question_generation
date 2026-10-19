import React, { useState } from 'react';
import { HelpCircle, Send, CheckCircle2, AlertTriangle, Play, Sparkles } from 'lucide-react';
import { api } from '../../shared/api/client';
import { VideoQAAnswer } from '../../shared/types';

interface GroundedQAPanelProps {
  videoId: string | null;
  analysisId?: string | null;
  onSeekInterval: (interval: { start: number; end: number }) => void;
}

export const GroundedQAPanel: React.FC<GroundedQAPanelProps> = ({
  videoId,
  analysisId,
  onSeekInterval,
}) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [answers, setAnswers] = useState<VideoQAAnswer[]>([]);
  const [error, setError] = useState<string | null>(null);

  const suggestedQuestions = [
    'Who was the first person to interact with an object?',
    'Did anyone pick up or move an item?',
    'What action occurred at the beginning?',
    'When did someone leave or enter?',
  ];

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q || !videoId) return;

    setLoading(true);
    setError(null);

    try {
      const res = await api.askVideoQuestion(videoId, q, analysisId || undefined);
      setAnswers((prev) => [res, ...prev]);
      if (!queryText) setQuestion('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Question answering failed');
    } finally {
      setLoading(false);
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col space-y-4">
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
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

      {/* Suggested prompts */}
      <div className="flex flex-wrap gap-1.5">
        {suggestedQuestions.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleAsk(s)}
            disabled={loading || !videoId}
            className="text-[11px] bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white px-2.5 py-1 rounded-md border border-slate-700/60 transition"
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
          placeholder="Ask anything about what happens in the video..."
          disabled={loading || !videoId}
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
        />

        <button
          onClick={() => handleAsk()}
          disabled={loading || !question.trim() || !videoId}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg transition flex items-center space-x-1.5 shadow"
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

      {/* Answers list */}
      <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
        {answers.map((ans, idx) => (
          <div
            key={idx}
            className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 space-y-2 text-xs"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-300">{ans.question}</span>

              {ans.is_observable ? (
                <span className="flex items-center space-x-1 text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>Observable Fact ({(ans.confidence * 100).toFixed(0)}%)</span>
                </span>
              ) : (
                <span className="flex items-center space-x-1 text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded-full">
                  <AlertTriangle className="w-2.5 h-2.5" />
                  <span>Uncertain / Not Visible</span>
                </span>
              )}
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

