import React, { useState, useEffect } from 'react';
import {
  Scissors,
  Play,
  RotateCcw,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  HardDrive,
  Info,
} from 'lucide-react';
import { VideoIntervalSelection, LocalVideoItem } from '../../shared/types';
import {
  formatTimestamp,
  parseTimestamp,
  validateInterval,
  formatDuration,
  generateSelectionId,
} from './timestampUtils';

export interface ClipSelectionPanelProps {
  localVideo: LocalVideoItem;
  currentTime: number;
  videoDuration: number;
  selections: VideoIntervalSelection[];
  activeInterval: { start: number; end: number } | null;
  onAddSelection: (selection: VideoIntervalSelection) => void;
  onUpdateSelection: (selection: VideoIntervalSelection) => void;
  onRemoveSelection: (id: string) => void;
  onPreviewInterval: (interval: { start: number; end: number }) => void;
  onJumpTo: (timestamp: number, autoPlay?: boolean) => void;
  onClearActiveInterval: () => void;
  onOpenExtraction?: (interval: { start: number; end: number; label?: string }) => void;
}

export const ClipSelectionPanel: React.FC<ClipSelectionPanelProps> = ({
  localVideo,
  currentTime,
  videoDuration,
  selections,
  activeInterval,
  onAddSelection,
  onUpdateSelection,
  onRemoveSelection,
  onPreviewInterval,
  onJumpTo,
  onClearActiveInterval,
  onOpenExtraction,
}) => {
  const effectiveDuration = videoDuration > 0 ? videoDuration : 100;
  const videoRefKey = localVideo.sourceInstanceId || `${localVideo.filename}-${localVideo.sizeBytes}`;

  // Local draft state for interval editor
  const [startSeconds, setStartSeconds] = useState<number>(0);
  const [endSeconds, setEndSeconds] = useState<number>(Math.min(10, effectiveDuration));
  const [startInputText, setStartInputText] = useState<string>(formatTimestamp(0));
  const [endInputText, setEndInputText] = useState<string>(
    formatTimestamp(Math.min(10, effectiveDuration))
  );
  const [label, setLabel] = useState<string>('');
  const [editingSelectionId, setEditingSelectionId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Sync inputs when effectiveDuration loads if end was default
  useEffect(() => {
    if (videoDuration > 0 && endSeconds > videoDuration) {
      const clampedEnd = Math.round(videoDuration * 1000) / 1000;
      setEndSeconds(clampedEnd);
      setEndInputText(formatTimestamp(clampedEnd));
    }
  }, [videoDuration]);

  // Handle Mark Start using current playback time
  const handleMarkStart = () => {
    const clampedCurrent = Math.round(currentTime * 1000) / 1000;
    setStartSeconds(clampedCurrent);
    setStartInputText(formatTimestamp(clampedCurrent));
    setValidationError(null);
  };

  // Handle Mark End using current playback time
  const handleMarkEnd = () => {
    const clampedCurrent = Math.round(currentTime * 1000) / 1000;
    setEndSeconds(clampedCurrent);
    setEndInputText(formatTimestamp(clampedCurrent));
    setValidationError(null);
  };

  // Handle Manual Start Text Change
  const handleStartTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    setStartInputText(text);
    const parsed = parseTimestamp(text);
    if (parsed !== null) {
      setStartSeconds(parsed);
      setValidationError(null);
    } else {
      setValidationError('Start timestamp must be in format HH:MM:SS.mmm or numeric seconds.');
    }
  };

  // Handle Manual End Text Change
  const handleEndTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    setEndInputText(text);
    const parsed = parseTimestamp(text);
    if (parsed !== null) {
      setEndSeconds(parsed);
      setValidationError(null);
    } else {
      setValidationError('End timestamp must be in format HH:MM:SS.mmm or numeric seconds.');
    }
  };

  // Handle Start Slider Scrub
  const handleStartSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setStartSeconds(val);
    setStartInputText(formatTimestamp(val));
    setValidationError(null);
  };

  // Handle End Slider Scrub
  const handleEndSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setEndSeconds(val);
    setEndInputText(formatTimestamp(val));
    setValidationError(null);
  };

  // Jump to start boundary
  const handleJumpToStart = () => {
    onJumpTo(startSeconds, false);
  };

  // Jump to end boundary
  const handleJumpToEnd = () => {
    onJumpTo(endSeconds, false);
  };

  // Preview Interval
  const handlePreview = () => {
    const validation = validateInterval(startSeconds, endSeconds, videoDuration, 600);
    if (!validation.isValid) {
      setValidationError(validation.error);
      return;
    }
    setValidationError(null);
    onPreviewInterval({ start: startSeconds, end: endSeconds });
  };

  // Add or Update Selection
  const handleSaveSelection = () => {
    const validation = validateInterval(startSeconds, endSeconds, videoDuration, 600);
    if (!validation.isValid) {
      setValidationError(validation.error);
      return;
    }

    const duration = Math.round((endSeconds - startSeconds) * 1000) / 1000;

    if (editingSelectionId) {
      const updated: VideoIntervalSelection = {
        id: editingSelectionId,
        videoRef: videoRefKey,
        startSeconds,
        endSeconds,
        durationSeconds: duration,
        label: label.trim() || undefined,
        createdAt: new Date().toISOString(),
      };
      onUpdateSelection(updated);
      setEditingSelectionId(null);
    } else {
      const newSelection: VideoIntervalSelection = {
        id: generateSelectionId(),
        videoRef: videoRefKey,
        startSeconds,
        endSeconds,
        durationSeconds: duration,
        label: label.trim() || undefined,
        createdAt: new Date().toISOString(),
      };
      onAddSelection(newSelection);
    }

    setLabel('');
    setValidationError(null);
  };

  // Load a saved selection into editor
  const handleEditSelection = (sel: VideoIntervalSelection) => {
    setEditingSelectionId(sel.id);
    setStartSeconds(sel.startSeconds);
    setEndSeconds(sel.endSeconds);
    setStartInputText(formatTimestamp(sel.startSeconds));
    setEndInputText(formatTimestamp(sel.endSeconds));
    setLabel(sel.label || '');
    setValidationError(null);
    onPreviewInterval({ start: sel.startSeconds, end: sel.endSeconds });
  };

  // Reset editor
  const handleClearSelection = () => {
    setEditingSelectionId(null);
    setStartSeconds(0);
    setEndSeconds(Math.min(10, effectiveDuration));
    setStartInputText(formatTimestamp(0));
    setEndInputText(formatTimestamp(Math.min(10, effectiveDuration)));
    setLabel('');
    setValidationError(null);
    onClearActiveInterval();
  };

  const calculatedDuration = Math.max(0, endSeconds - startSeconds);
  const startPercent = Math.min(100, Math.max(0, (startSeconds / effectiveDuration) * 100));
  const endPercent = Math.min(100, Math.max(0, (endSeconds / effectiveDuration) * 100));
  const currentPercent = Math.min(100, Math.max(0, (currentTime / effectiveDuration) * 100));

  return (
    <div
      data-testid="clip-selection-panel"
      className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4 shadow-lg text-slate-200"
    >
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
            <Scissors className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-white tracking-wide uppercase">
              Interactive Clip Selection
            </h3>
            <p className="text-[11px] text-slate-400">
              Mark interesting video timestamps locally. The original video never leaves your computer.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-mono bg-slate-800 border border-slate-700 text-emerald-400">
            <Clock className="w-3 h-3 text-emerald-400" />
            <span data-testid="current-time-display">Current: {formatTimestamp(currentTime)}</span>
          </span>
        </div>
      </div>

      {/* Interactive Dual-Range Timeline Visualization */}
      <div className="space-y-2 bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80">
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>00:00:00.000</span>
          <span className="text-indigo-300 font-medium">
            Selected Interval: {formatDuration(calculatedDuration)}
          </span>
          <span>{formatTimestamp(videoDuration || effectiveDuration)}</span>
        </div>

        {/* Visual Track */}
        <div className="relative w-full h-4 bg-slate-800 rounded-full overflow-hidden select-none">
          {/* Active Selection Band */}
          <div
            data-testid="timeline-selection-band"
            className="absolute top-0 bottom-0 bg-indigo-500/40 border-x-2 border-indigo-400"
            style={{
              left: `${Math.min(startPercent, endPercent)}%`,
              width: `${Math.abs(endPercent - startPercent)}%`,
            }}
          />

          {/* Current Playback Needle */}
          <div
            data-testid="timeline-current-needle"
            className="absolute top-0 bottom-0 w-1 bg-amber-400 shadow-sm z-10"
            style={{ left: `${currentPercent}%` }}
            title={`Current: ${formatTimestamp(currentTime)}`}
          />
        </div>

        {/* Dual Range Controls (Keyboard Accessible) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <div>
            <label className="text-[11px] font-medium text-slate-400 block mb-1">
              Start Handle: <span className="text-white font-mono">{formatTimestamp(startSeconds)}</span>
            </label>
            <input
              type="range"
              min={0}
              max={effectiveDuration}
              step={0.1}
              value={startSeconds}
              onChange={handleStartSliderChange}
              aria-label="Selection start timestamp slider"
              data-testid="start-range-slider"
              className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>

          <div>
            <label className="text-[11px] font-medium text-slate-400 block mb-1">
              End Handle: <span className="text-white font-mono">{formatTimestamp(endSeconds)}</span>
            </label>
            <input
              type="range"
              min={0}
              max={effectiveDuration}
              step={0.1}
              value={endSeconds}
              onChange={handleEndSliderChange}
              aria-label="Selection end timestamp slider"
              data-testid="end-range-slider"
              className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* Manual Input Fields & Boundary Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Start Timestamp Control */}
        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-300">Start Timestamp</span>
            <div className="flex items-center space-x-1.5">
              <button
                type="button"
                onClick={handleMarkStart}
                data-testid="mark-start-btn"
                className="px-2 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded border border-slate-700 transition"
                title="Mark start at current video playback position"
              >
                Mark Start
              </button>
              <button
                type="button"
                onClick={handleJumpToStart}
                data-testid="jump-to-start-btn"
                className="px-2 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
                title="Jump video player to start timestamp"
              >
                Jump
              </button>
            </div>
          </div>
          <input
            type="text"
            value={startInputText}
            onChange={handleStartTextChange}
            aria-label="Start timestamp in HH:MM:SS.mmm"
            data-testid="start-timestamp-input"
            placeholder="00:00:00.000"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* End Timestamp Control */}
        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-300">End Timestamp</span>
            <div className="flex items-center space-x-1.5">
              <button
                type="button"
                onClick={handleMarkEnd}
                data-testid="mark-end-btn"
                className="px-2 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded border border-slate-700 transition"
                title="Mark end at current video playback position"
              >
                Mark End
              </button>
              <button
                type="button"
                onClick={handleJumpToEnd}
                data-testid="jump-to-end-btn"
                className="px-2 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
                title="Jump video player to end timestamp"
              >
                Jump
              </button>
            </div>
          </div>
          <input
            type="text"
            value={endInputText}
            onChange={handleEndTextChange}
            aria-label="End timestamp in HH:MM:SS.mmm"
            data-testid="end-timestamp-input"
            placeholder="00:00:10.000"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Optional Label & Validation Error */}
      <div className="space-y-1.5">
        <label className="text-[11px] font-medium text-slate-400 block">
          Optional Selection Label
        </label>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. Person enters kitchen, suspect takes keycard"
          data-testid="selection-label-input"
          className="w-full bg-slate-950/60 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {validationError && (
        <div
          data-testid="selection-validation-error"
          className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/50 p-2.5 rounded-lg flex items-center space-x-2"
        >
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Action Buttons Row */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800">
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={handlePreview}
            data-testid="preview-selection-btn"
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow transition flex items-center space-x-1.5"
            title="Preview playback from start to end boundary"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Preview Selection</span>
          </button>

          <button
            type="button"
            onClick={handleSaveSelection}
            data-testid="add-selection-btn"
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs font-semibold rounded-lg border border-slate-700 transition flex items-center space-x-1.5"
          >
            {editingSelectionId ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
            <span>{editingSelectionId ? 'Update Selection' : 'Add Selection'}</span>
          </button>

          <button
            type="button"
            onClick={handleClearSelection}
            data-testid="clear-selection-btn"
            className="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-white text-xs rounded-lg transition"
            title="Reset interval editor"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Extraction Action */}
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => {
              if (onOpenExtraction) {
                onOpenExtraction({ start: startSeconds, end: endSeconds, label });
              }
            }}
            data-testid="extract-clip-btn"
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow transition flex items-center space-x-1.5"
            title="Prepare short clips for this selected interval"
          >
            <Scissors className="w-3.5 h-3.5" />
            <span>Prepare Analysis Clips</span>
          </button>
        </div>
      </div>

      {/* Saved Intervals List */}
      <div className="space-y-2 pt-2 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-slate-300">
            Saved Intervals ({selections.length})
          </h4>
          <span className="text-[11px] text-slate-500">
            {selections.length === 0
              ? 'No intervals saved yet'
              : `${selections.length} interval${selections.length > 1 ? 's' : ''} ready for extraction`}
          </span>
        </div>

        {selections.length === 0 ? (
          <div
            data-testid="no-selections-message"
            className="p-3 bg-slate-950/40 border border-slate-800/60 rounded-lg text-center text-xs text-slate-500"
          >
            Mark start and end timestamps above, then click &quot;Add Selection&quot; to save an interesting interval.
          </div>
        ) : (
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {selections.map((sel, idx) => {
              const isActive =
                activeInterval &&
                Math.abs(activeInterval.start - sel.startSeconds) < 0.05 &&
                Math.abs(activeInterval.end - sel.endSeconds) < 0.05;

              return (
                <div
                  key={sel.id}
                  data-testid={`selection-item-${sel.id}`}
                  className={`p-2.5 rounded-lg border transition flex items-center justify-between ${
                    isActive
                      ? 'bg-indigo-950/40 border-indigo-500/50 text-white'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="space-y-0.5 truncate mr-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-[11px] font-bold text-indigo-400 font-mono">
                        Selection {idx + 1}
                      </span>
                      {sel.label && (
                        <span className="text-xs font-medium text-slate-200 truncate">
                          — {sel.label}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400">
                      <span>
                        {formatTimestamp(sel.startSeconds)} → {formatTimestamp(sel.endSeconds)}
                      </span>
                      <span className="text-emerald-400 font-semibold">
                        ({formatDuration(sel.durationSeconds)})
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        if (onOpenExtraction) {
                          onOpenExtraction({ start: sel.startSeconds, end: sel.endSeconds, label: sel.label });
                        }
                      }}
                      data-testid={`extract-selection-${sel.id}`}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-indigo-400 hover:text-indigo-300 transition"
                      title="Extract this saved interval"
                    >
                      <Scissors className="w-3.5 h-3.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => onPreviewInterval({ start: sel.startSeconds, end: sel.endSeconds })}
                      data-testid={`preview-selection-${sel.id}`}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-indigo-300 transition"
                      title="Preview this interval"
                    >
                      <Play className="w-3.5 h-3.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => handleEditSelection(sel)}
                      data-testid={`edit-selection-${sel.id}`}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                      title="Edit this interval in editor"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => onRemoveSelection(sel.id)}
                      data-testid={`remove-selection-${sel.id}`}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
                      title="Remove this interval"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

