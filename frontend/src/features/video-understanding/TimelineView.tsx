import React, { useState } from 'react';
import {
  Clock,
  Play,
  User,
  Target,
  Box,
  Sparkles,
  AlertTriangle,
  Copy,
  Check,
  Bookmark,
  BookmarkCheck,
  FileText,
} from 'lucide-react';
import { VideoAnalysis } from '../../shared/types';
import { api } from '../../shared/api/client';

interface TimelineViewProps {
  analysis: VideoAnalysis | null;
  currentTime: number;
  onSelectInterval: (interval: { start: number; end: number }) => void;
  onRunAnalysis?: () => void;
  isAnalyzing?: boolean;
  onAnalysisUpdated?: (updated: VideoAnalysis) => void;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
  analysis,
  currentTime,
  onSelectInterval,
  onRunAnalysis,
  isAnalyzing,
  onAnalysisUpdated,
}) => {
  const [summaryCopied, setSummaryCopied] = useState(false);
  const [copiedEventIndex, setCopiedEventIndex] = useState<number | null>(null);
  const [isSavingPersistent, setIsSavingPersistent] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  const handleCopySummary = async () => {
    if (!analysis) return;
    try {
      await navigator.clipboard.writeText(analysis.summary);
      setSummaryCopied(true);
      window.setTimeout(() => setSummaryCopied(false), 1800);
    } catch {
      // Clipboard permissions may be unavailable in an embedded browser.
    }
  };

  const handleCopyEvent = async (eventIndex: number, description: string) => {
    try {
      await navigator.clipboard.writeText(description);
      setCopiedEventIndex(eventIndex);
      window.setTimeout(() => setCopiedEventIndex((current) => current === eventIndex ? null : current), 1800);
    } catch {
      // Keep the timeline usable if clipboard permissions are unavailable.
    }
  };

  const handleSaveToLibrary = async () => {
    if (!analysis || isSavingPersistent) return;
    setIsSavingPersistent(true);
    try {
      const updated = await api.saveAnalysisPersistent(analysis.analysis_id);
      if (onAnalysisUpdated) {
        onAnalysisUpdated(updated);
      }
      setSaveSuccess(true);
    } catch (err) {
      console.error('Failed to save analysis permanently', err);
    } finally {
      setIsSavingPersistent(false);
    }
  };

  if (!analysis) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center flex flex-col items-center justify-center">
        <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl mb-3 border border-indigo-500/20">
          <Sparkles className="w-6 h-6" />
        </div>
        <h3 className="text-base font-medium text-white mb-1">No Analysis Available</h3>
        <p className="text-xs text-slate-400 max-w-sm mb-4">
          Run Qwen2.5-VL video understanding on a staged short clip or server video to extract a chronological timeline of observable events and factual descriptions.
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

  const isPersistent = analysis.is_persistent || saveSuccess;
  const chronologicalEvents = analysis.events
    .map((event, sourceIndex) => ({ event, sourceIndex }))
    .sort((left, right) => {
      const leftTime = left.event.source_start_seconds ?? left.event.start_seconds;
      const rightTime = right.event.source_start_seconds ?? right.event.start_seconds;
      return leftTime - rightTime || left.sourceIndex - right.sourceIndex;
    });

  return (
    <div className="min-w-0 w-full bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col space-y-4">
      {/* Prominent MOCK / TEST DATA Notice when simulated */}
      {analysis.is_mock && (
        <div
          data-testid="mock-inference-banner"
          className="flex items-start space-x-2.5 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs"
        >
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold tracking-wide">MOCK / TEST DATA — NOT REAL VIDEO ANALYSIS</span>
            <p className="text-[11px] text-amber-400/80 mt-0.5">
              These events and observations were generated by deterministic simulation for development and testing. They do not represent genuine visual observations from Qwen2.5-VL.
            </p>
          </div>
          {analysis.sampling_fps !== undefined && analysis.sampling_fps !== null && (
            <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded font-mono shrink-0">
              Sample: {analysis.sampling_fps} FPS
            </span>
          )}
        </div>
      )}

      {/* Legacy / Unverified Provenance Notice */}
      {!analysis.is_mock && (analysis.inference_mode === 'legacy_unverified' || analysis.inference_mode === 'unknown') && (
        <div
          data-testid="legacy-unverified-banner"
          className="flex items-start space-x-2.5 p-3 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 text-xs"
        >
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold tracking-wide text-amber-300">HISTORICAL DATA — PROVENANCE UNVERIFIED</span>
            <p className="text-[11px] text-slate-400 mt-0.5">
              This analysis was loaded from a historical artifact without recorded inference provenance. It cannot be used as verified training ground truth until independently confirmed.
            </p>
          </div>
          <span className="text-[10px] bg-slate-700 text-slate-300 border border-slate-600 px-2 py-0.5 rounded font-mono shrink-0">
            Legacy Archive
          </span>
        </div>
      )}

      {/* Header Info & Actions Toolbar */}
      <div className="border-b border-slate-800 pb-3 space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-white">Chronological Event Timeline</h2>
              <span className="text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                {analysis.events.length} events
              </span>
              {analysis.is_temporary && (
                <span className="text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-1.5 py-0.5 rounded font-mono">
                  Temporary Clip
                </span>
              )}
              {analysis.is_mock ? (
                <span
                  data-testid="mock-inference-badge"
                  className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1.5 py-0.5 rounded font-mono font-medium"
                >
                  Mock Engine
                </span>
              ) : (analysis.inference_mode === 'legacy_unverified' || analysis.inference_mode === 'unknown') ? (
                <span
                  data-testid="legacy-unverified-badge"
                  className="text-[10px] bg-slate-700 text-slate-300 border border-slate-600 px-1.5 py-0.5 rounded font-mono font-medium"
                >
                  Legacy Unverified
                </span>
              ) : (
                <span
                  data-testid="real-inference-badge"
                  className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-1.5 py-0.5 rounded font-mono font-medium"
                >
                  Real Qwen2.5-VL
                </span>
              )}
              {isPersistent && (
                <span
                  data-testid="analysis-persistent-badge"
                  className="text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded font-mono flex items-center space-x-1"
                >
                  <BookmarkCheck className="w-3 h-3 text-emerald-400" />
                  <span>Saved in Library</span>
                </span>
              )}
              {analysis.video_available === false && (
                <span
                  data-testid="analysis-video-unavailable-badge"
                  className="text-[10px] bg-amber-500/10 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded font-mono flex items-center space-x-1"
                >
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                  <span>Original clip expired (results preserved)</span>
                </span>
              )}
            </div>
          </div>

          {analysis.scene && (
            <span className="min-w-0 max-w-full whitespace-normal break-words text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2.5 py-1 rounded-md font-mono sm:max-w-[52%]">
              {analysis.scene}
            </span>
          )}
        </div>

        {/* Source mapping metadata if available */}
        {analysis.source_video_name && (
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-400 font-mono">
            <span className="text-emerald-400 font-semibold">Source: {analysis.source_video_name}</span>
            {analysis.source_start_seconds !== undefined && analysis.source_start_seconds !== null && (
              <span className="text-slate-300">
                ({formatSeconds(analysis.source_start_seconds)} → {formatSeconds(analysis.source_end_seconds || 0)})
              </span>
            )}
            {analysis.temporal_alignment_status && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {analysis.temporal_alignment_status}
              </span>
            )}
          </div>
        )}

        <section className="min-w-0 rounded-lg border border-slate-800 bg-slate-950/50 p-3" aria-label="Video summary">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="text-xs font-semibold text-slate-200">Video Summary</h3>
              <p className="mt-1.5 break-words text-sm leading-relaxed text-slate-300">{analysis.summary}</p>
            </div>
            <button
              onClick={handleCopySummary}
              data-testid="copy-summary-btn"
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1.5 text-xs text-slate-300 transition hover:bg-slate-700/80 hover:text-white"
              title="Copy video summary to clipboard"
            >
              {summaryCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <FileText className="w-3.5 h-3.5 text-slate-400" />}
              <span>{summaryCopied ? 'Copied Summary' : 'Copy Summary'}</span>
            </button>
          </div>
        </section>

        {/* Participants & Objects Chips */}
        {((analysis.participants && analysis.participants.length > 0) ||
          (analysis.objects && analysis.objects.length > 0)) && (
          <div className="flex flex-wrap items-center gap-1.5">
            {analysis.participants?.map((participant, pIdx) => (
              <span
                key={`p-${pIdx}`}
                className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] bg-indigo-950/40 text-indigo-300 border border-indigo-800/40"
              >
                <User className="w-2.5 h-2.5 text-indigo-400" />
                <span>{participant}</span>
              </span>
            ))}
            {analysis.objects?.map((objectItem, oIdx) => (
              <span
                key={`o-${oIdx}`}
                className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] bg-amber-950/40 text-amber-300 border border-amber-800/40"
              >
                <Box className="w-2.5 h-2.5 text-amber-400" />
                <span>{objectItem}</span>
              </span>
            ))}
          </div>
        )}

        {/* Optional retention control for temporary analysis results */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/60">
          <span className="text-[11px] text-slate-500">{analysis.events.length} chronological events</span>

          {/* Explicit Save button for temporary analyses */}
          {analysis.is_temporary && !isPersistent && (
            <button
              onClick={handleSaveToLibrary}
              disabled={isSavingPersistent}
              data-testid="save-analysis-persistent-btn"
              className="flex items-center space-x-1.5 text-xs text-indigo-200 hover:text-white bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-700/60 px-3 py-1 rounded-lg transition shadow-sm font-medium"
              title="Promote this temporary analysis to permanent storage"
            >
              {isSavingPersistent ? (
                <span className="w-3 h-3 border-2 border-indigo-400/40 border-t-indigo-400 rounded-full animate-spin" />
              ) : (
                <Bookmark className="w-3.5 h-3.5 text-indigo-400" />
              )}
              <span>Save to Library</span>
            </button>
          )}
        </div>
      </div>

      {/* Events List */}
      <div className="min-w-0 space-y-3 max-h-[460px] overflow-y-auto pr-1">
        {chronologicalEvents.map(({ event, sourceIndex: idx }) => {
          const clipStart = event.clip_start_seconds ?? event.start_seconds;
          const clipEnd = event.clip_end_seconds ?? event.end_seconds;
          const hasSourceMapping =
            event.source_start_seconds !== null && event.source_start_seconds !== undefined;
          const sourceStart = event.source_start_seconds ?? 0;
          const sourceEnd = event.source_end_seconds ?? 0;
          const uncertainty = event.time_offset_uncertainty ?? 0;

          const isActive = hasSourceMapping
            ? (currentTime >= sourceStart && currentTime <= sourceEnd) ||
              (currentTime >= clipStart && currentTime <= clipEnd)
            : currentTime >= clipStart && currentTime <= clipEnd;

          return (
            <div
              key={idx}
              className={`min-w-0 p-3 rounded-lg border transition ${
                isActive
                  ? 'bg-indigo-950/40 border-indigo-500/50 shadow-md'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                  {/* Clip relative timestamp */}
                  <span
                    data-testid="event-clip-time"
                    className="font-mono text-xs text-indigo-400 bg-indigo-950/60 border border-indigo-800/60 px-2 py-0.5 rounded flex items-center space-x-1"
                    title="Clip-relative interval"
                  >
                    <Clock className="w-3 h-3" />
                    <span>
                      {formatSeconds(clipStart)} - {formatSeconds(clipEnd)}
                    </span>
                  </span>

                  {/* Source mapped timestamp */}
                  {hasSourceMapping && (
                    <span
                      data-testid="event-source-time"
                      className="font-mono text-xs text-emerald-400 bg-emerald-950/50 border border-emerald-800/50 px-2 py-0.5 rounded flex items-center space-x-1"
                      title="Source-mapped interval in original long video"
                    >
                      <Clock className="w-3 h-3" />
                      <span>Source: {formatSeconds(sourceStart)} - {formatSeconds(sourceEnd)}</span>
                    </span>
                  )}

                  {/* Uncertainty badge */}
                  {uncertainty > 0 && (
                    <span
                      data-testid="event-uncertainty-badge"
                      className="text-[10px] text-amber-300 font-mono bg-amber-950/40 border border-amber-800/40 px-1.5 py-0.5 rounded flex items-center space-x-1"
                      title={`Temporal offset uncertainty of ±${uncertainty.toFixed(2)}s`}
                    >
                      <AlertTriangle className="w-2.5 h-2.5 text-amber-400" />
                      <span>±{uncertainty.toFixed(2)}s offset</span>
                    </span>
                  )}

                  {event.confidence !== null && event.confidence !== undefined && (
                    <span className="text-[10px] text-emerald-400 font-mono bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.5 rounded">
                      {(event.confidence * 100).toFixed(0)}% conf
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-1.5 sm:ml-2 sm:shrink-0">
                  <button
                    onClick={() =>
                      onSelectInterval({
                        start: hasSourceMapping ? sourceStart : clipStart,
                        end: hasSourceMapping ? sourceEnd : clipEnd,
                      })
                    }
                    data-testid={`play-event-interval-${idx}`}
                    className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-800 px-2.5 py-1 rounded transition"
                    title={hasSourceMapping ? 'Seek to event in source video' : 'Seek to event in clip'}
                  >
                    <Play className="w-3 h-3" />
                    <span>{hasSourceMapping ? 'Play in source' : 'Play interval'}</span>
                  </button>
                  <button
                    onClick={() => void handleCopyEvent(idx, event.description)}
                    data-testid={`copy-event-${idx}`}
                    aria-label={`Copy event ${idx + 1} description`}
                    className="inline-flex items-center gap-1 rounded bg-slate-800/80 px-2.5 py-1 text-xs text-slate-400 transition hover:bg-slate-800 hover:text-white"
                    title="Copy only this event description"
                  >
                    {copiedEventIndex === idx ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedEventIndex === idx ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              <p data-testid={`event-description-${idx}`} className="mb-2 min-w-0 break-words text-xs font-medium leading-relaxed text-slate-200">
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
                {(event.object || event.object_name) && (
                  <span className="flex items-center space-x-1 bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                    <Box className="w-2.5 h-2.5 text-amber-400" />
                    <span>{event.object || event.object_name}</span>
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
