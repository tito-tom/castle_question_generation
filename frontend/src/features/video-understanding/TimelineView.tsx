import React from 'react';
import { Clock, Play, User, Target, Box, Sparkles } from 'lucide-react';
import { ObservableEvent, VideoAnalysis } from '../../shared/types';

interface TimelineViewProps {
  analysis: VideoAnalysis | null;
  currentTime: number;
  onSelectInterval: (interval: { start: number; end: number }) => void;
  onRunAnalysis?: () => void;
  isAnalyzing?: boolean;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
  analysis,
  currentTime,
  onSelectInterval,
  onRunAnalysis,
  isAnalyzing,
}) => {
  if (!analysis) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center flex flex-col items-center justify-center">
        <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl mb-3 border border-indigo-500/20">
          <Sparkles className="w-6 h-6" />
        </div>
        <h3 className="text-base font-medium text-white mb-1">No Analysis Available</h3>
        <p className="text-xs text-slate-400 max-w-sm mb-4">
          Run Qwen2.5-VL video understanding to extract a chronological timeline of observable events and factual descriptions.
        </p>
        {onRunAnalysis && (
          <button
            onClick={onRunAnalysis}
            disabled={isAnalyzing}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg transition shadow flex items-center space-x-2"
          >
            {isAnalyzing ? (
              <>
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                <span>Extracting Events...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Run Qwen Video Understanding</span>
              </>
            )}
          </button>
        )}
      </div>
    );
  }

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col space-y-4">
      {/* Header Info */}
      <div className="border-b border-slate-800 pb-3 flex items-start justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-sm font-semibold text-white">Chronological Event Timeline</h2>
            <span className="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
              {analysis.events.length} events
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">{analysis.summary}</p>
        </div>

        {analysis.scene && (
          <span className="text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2.5 py-1 rounded-md font-mono">
            {analysis.scene}
          </span>
        )}
      </div>

      {/* Events List */}
      <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
        {analysis.events.map((event, idx) => {
          const isActive =
            currentTime >= event.start_seconds && currentTime <= event.end_seconds;

          return (
            <div
              key={idx}
              className={`p-3 rounded-lg border transition ${
                isActive
                  ? 'bg-indigo-950/40 border-indigo-500/50 shadow-md'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs text-indigo-400 bg-indigo-950/60 border border-indigo-800/60 px-2 py-0.5 rounded flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>
                      {formatSeconds(event.start_seconds)} - {formatSeconds(event.end_seconds)}
                    </span>
                  </span>

                  {event.confidence !== null && event.confidence !== undefined && (
                    <span className="text-[10px] text-emerald-400 font-mono bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.5 rounded">
                      {(event.confidence * 100).toFixed(0)}% conf
                    </span>
                  )}
                </div>

                <button
                  onClick={() =>
                    onSelectInterval({
                      start: event.start_seconds,
                      end: event.end_seconds,
                    })
                  }
                  className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-800 px-2.5 py-1 rounded transition"
                >
                  <Play className="w-3 h-3" />
                  <span>Play interval</span>
                </button>
              </div>

              <p className="text-xs text-slate-200 font-medium leading-relaxed mb-2">
                {event.description}
              </p>

              {/* Entity Chips */}
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                {event.actor && (
                  <span className="flex items-center space-x-1 bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                    <User className="w-2.5 h-2.5 text-indigo-400" />
                    <span>{event.actor}</span>
                  </span>
                )}
                {event.action && (
                  <span className="bg-slate-800/80 text-slate-400 px-2 py-0.5 rounded border border-slate-700/60">
                    action: {event.action}
                  </span>
                )}
                {event.object && (
                  <span className="flex items-center space-x-1 bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                    <Box className="w-2.5 h-2.5 text-amber-400" />
                    <span>{event.object}</span>
                  </span>
                )}
                {event.target && (
                  <span className="flex items-center space-x-1 bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                    <Target className="w-2.5 h-2.5 text-rose-400" />
                    <span>{event.target}</span>
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

