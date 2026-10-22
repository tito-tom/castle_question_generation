import React from 'react';
import { CheckCircle2, Circle, Download, Loader2, Play, RotateCcw, Trash2, X } from 'lucide-react';
import { StagedClipItem } from '../../shared/types';
import { formatTimestamp } from './timestampUtils';

export type WindowTaskStatus = 'ready' | 'uploading' | 'processing' | 'completed' | 'failed';
export interface WindowTaskState { status: WindowTaskStatus; analysisId?: string; error?: string; }

interface Props {
  clips: StagedClipItem[];
  states: Record<string, WindowTaskState>;
  isAnalyzing: boolean;
  progressText: string;
  batchError?: string | null;
  onAnalyze: () => void;
  onCancel: () => void;
  onClear: () => void;
}

export const WindowedClipBatchCard: React.FC<Props> = ({ clips, states, isAnalyzing, progressText, batchError, onAnalyze, onCancel, onClear }) => {
  const completed = clips.filter((clip) => states[clip.id]?.status === 'completed').length;
  const failed = clips.some((clip) => states[clip.id]?.status === 'failed');
  return (
    <section data-testid="windowed-clip-batch" className="rounded-2xl border border-indigo-500/40 bg-slate-900 p-5 shadow-lg">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-300">Selected interval task</p>
          <h3 className="mt-1 text-lg font-semibold text-white">{completed === clips.length ? 'Analysis windows complete' : `${clips.length} analysis windows`}</h3>
          <p className="mt-1 text-sm text-slate-400">Each short clip uploads temporarily and is deleted after its worker finishes. Original recording remains local.</p>
        </div>
        <button onClick={onClear} disabled={isAnalyzing} aria-label="Clear prepared windows" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-rose-300 disabled:opacity-40"><Trash2 className="h-4 w-4" /></button>
      </div>

      <div className="my-4 grid gap-2 sm:grid-cols-2">
        {clips.map((clip, index) => {
          const state = states[clip.id]?.status || 'ready';
          return <div key={clip.id} data-testid={`analysis-window-${index + 1}`} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
            {state === 'completed' ? <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" /> : state === 'uploading' || state === 'processing' ? <Loader2 className="h-5 w-5 shrink-0 animate-spin text-indigo-300" /> : state === 'failed' ? <RotateCcw className="h-5 w-5 shrink-0 text-rose-300" /> : <Circle className="h-5 w-5 shrink-0 text-slate-600" />}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-200">Window {String(index + 1).padStart(2, '0')} · {formatTimestamp(clip.sourceStartSeconds)}–{formatTimestamp(clip.sourceEndSeconds)}</p>
              <p className={`truncate text-xs ${state === 'failed' ? 'text-rose-300' : state === 'completed' ? 'text-emerald-300' : 'text-slate-500'}`}>{states[clip.id]?.error || clip.filename} · {state}</p>
            </div>
            <button type="button" onClick={() => { const anchor = document.createElement('a'); anchor.href = clip.objectUrl; anchor.download = clip.filename; anchor.click(); }} title="Download this prepared clip" className="rounded-md p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-200"><Download className="h-4 w-4" /></button>
          </div>;
        })}
      </div>

      {(isAnalyzing || failed || completed > 0) && <div className="mb-4 rounded-xl bg-slate-950/60 p-3">
        <div className="mb-2 flex justify-between text-xs text-slate-400"><span>{progressText || `${completed} of ${clips.length} windows analyzed`}</span><span>{completed}/{clips.length}</span></div>
        <div className="h-1.5 overflow-hidden rounded bg-slate-800"><div className="h-full rounded bg-emerald-500 transition-all" style={{ width: `${(completed / clips.length) * 100}%` }} /></div>
      </div>}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-xl text-xs text-slate-500">Mock inference is labeled in the results. Window results merge only exact duplicate events that overlap in time; no identity or event continuity is inferred across clips.</p>
        <div className="flex gap-2">
          {isAnalyzing && <button onClick={onCancel} className="inline-flex items-center gap-2 rounded-lg border border-rose-800/60 px-3 py-2 text-sm text-rose-200 hover:bg-rose-950/40"><X className="h-4 w-4" />Cancel</button>}
          {!isAnalyzing && (completed < clips.length || Boolean(batchError)) && <button onClick={onAnalyze} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"><Play className="h-4 w-4" />{completed === clips.length ? 'Retry merge' : failed || completed ? 'Retry remaining windows' : 'Analyze Selected Interval'}</button>}
        </div>
      </div>
    </section>
  );
};
