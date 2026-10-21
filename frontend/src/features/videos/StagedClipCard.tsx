import React, { useRef, useState } from 'react';
import {
  FileVideo,
  Download,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  HardDrive,
  Sparkles,
} from 'lucide-react';
import { StagedClipItem, formatFileSize } from '../../shared/types';
import { formatTimestamp, formatDuration } from './timestampUtils';

export interface StagedClipCardProps {
  stagedClip: StagedClipItem;
  onReplace: () => void;
  onClear: () => void;
  onAnalyzeClip?: (stagedClip: StagedClipItem) => void;
  isAnalyzing?: boolean;
  analysisProgressText?: string;
  uploadProgress?: number | null;
  analysisError?: string | null;
  onRetryAnalysis?: () => void;
}

const MAX_CLIP_SIZE_BYTES = 200 * 1024 * 1024; // 200 MB
const MAX_CLIP_DURATION_SECONDS = 120; // 120 seconds

export const StagedClipCard: React.FC<StagedClipCardProps> = ({
  stagedClip,
  onReplace,
  onClear,
  onAnalyzeClip,
  isAnalyzing = false,
  analysisProgressText,
  uploadProgress,
  analysisError,
  onRetryAnalysis,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const isSizeExceeded = stagedClip.sizeBytes > MAX_CLIP_SIZE_BYTES;
  const isDurationExceeded = stagedClip.durationSeconds > MAX_CLIP_DURATION_SECONDS;
  const isLimitsExceeded = isSizeExceeded || isDurationExceeded;

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = stagedClip.objectUrl;
    a.download = stagedClip.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const getMethodBadge = () => {
    switch (stagedClip.method) {
      case 'native_ffmpeg_assisted':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
            Native FFmpeg Assisted
          </span>
        );
      case 'browser_capture':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            Browser Capture (Experimental)
          </span>
        );
      case 'direct_import':
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
            Direct File Import
          </span>
        );
    }
  };

  const getAlignmentBadge = () => {
    switch (stagedClip.alignmentStatus) {
      case 'verified':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            <span>Alignment: Verified (Bitstream Analyzed)</span>
          </span>
        );
      case 'approximate':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3" />
            <span>Alignment: Approximate ({stagedClip.durationDeltaSeconds >= 0 ? '+' : ''}{stagedClip.durationDeltaSeconds.toFixed(2)}s)</span>
          </span>
        );
      case 'unverified':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30">
            <AlertTriangle className="w-3 h-3" />
            <span>Alignment: Unverified ({stagedClip.durationDeltaSeconds >= 0 ? '+' : ''}{stagedClip.durationDeltaSeconds.toFixed(2)}s)</span>
          </span>
        );
      case 'user_confirmed':
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-300 border border-blue-500/30">
            <Info className="w-3 h-3" />
            <span>Alignment: User-Confirmed</span>
          </span>
        );
    }
  };

  return (
    <div
      data-testid="staged-clip-card"
      className="bg-slate-900 border border-indigo-500/40 rounded-xl p-4 space-y-3.5 shadow-xl text-slate-200"
    >
      {/* Top Banner */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
            <FileVideo className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white tracking-wide uppercase">
              Staged Short Video Clip
            </h4>
            <p className="text-[11px] text-slate-400">
              Ready for preview and temporary Qwen video understanding. Only this short clip will be uploaded.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-1.5">
          <button
            type="button"
            onClick={handleDownload}
            data-testid="download-staged-clip-btn"
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Download extracted clip to your device"
          >
            <Download className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={onReplace}
            data-testid="replace-staged-clip-btn"
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Replace with another extraction or file"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={onClear}
            data-testid="clear-staged-clip-btn"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
            title="Remove staged clip"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Video Preview & Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Preview Screen */}
        <div className="aspect-video bg-black rounded-lg overflow-hidden border border-slate-800 relative">
          <video
            ref={videoRef}
            src={stagedClip.objectUrl}
            controls
            data-testid="staged-clip-video-player"
            className="w-full h-full object-contain"
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
          />
        </div>

        {/* Metadata & Provenance */}
        <div className="space-y-2 text-xs flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-1.5">
              {getMethodBadge()}
              {getAlignmentBadge()}
            </div>

            <div>
              <p className="font-semibold text-white truncate" title={stagedClip.filename}>
                {stagedClip.filename}
              </p>
              <p className="text-[11px] text-slate-400 font-mono">
                {formatFileSize(stagedClip.sizeBytes)} • {formatDuration(stagedClip.durationSeconds)} ({stagedClip.durationSeconds.toFixed(2)}s)
              </p>
            </div>

            <div className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 space-y-1 font-mono text-[11px]">
              <div className="flex justify-between text-slate-400">
                <span>Source:</span>
                <span className="text-slate-300 truncate max-w-[170px]" title={stagedClip.sourceVideoName}>
                  {stagedClip.sourceVideoName}
                </span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Target Interval:</span>
                <span className="text-indigo-300">
                  {formatTimestamp(stagedClip.sourceStartSeconds)} → {formatTimestamp(stagedClip.sourceEndSeconds)}
                </span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Target Duration:</span>
                <span className="text-slate-300">{stagedClip.sourceDurationSeconds.toFixed(1)}s</span>
              </div>
              {Math.abs(stagedClip.durationDeltaSeconds) > 0.05 && (
                <div className="flex justify-between text-amber-300">
                  <span>Duration Delta:</span>
                  <span>{stagedClip.durationDeltaSeconds >= 0 ? '+' : ''}{stagedClip.durationDeltaSeconds.toFixed(2)}s</span>
                </div>
              )}
              <div className="flex justify-between text-slate-400">
                <span>Association:</span>
                <span className="text-slate-300">
                  {stagedClip.userConfirmedAssociation ? 'User-Confirmed' : 'Pending'}
                </span>
              </div>
            </div>

            {/* Validation / Limit Warnings */}
            {isLimitsExceeded && (
              <div
                data-testid="clip-limit-warning"
                className="bg-rose-950/40 border border-rose-800/60 p-2.5 rounded-lg space-y-1 text-[11px] text-rose-200"
              >
                <div className="flex items-center space-x-1.5 font-semibold text-rose-300">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                  <span>Clip Limit Exceeded</span>
                </div>
                <p className="text-rose-200/90 leading-relaxed">
                  {isSizeExceeded && (
                    <span>
                      Clip size ({formatFileSize(stagedClip.sizeBytes)}) exceeds 200 MB maximum upload limit.{' '}
                    </span>
                  )}
                  {isDurationExceeded && (
                    <span>
                      Clip duration ({stagedClip.durationSeconds.toFixed(1)}s) exceeds 120s maximum limit.{' '}
                    </span>
                  )}
                  Please re-extract or trim a shorter interval before running Qwen.
                </p>
              </div>
            )}

            {/* Analysis Error Banner */}
            {analysisError && (
              <div
                data-testid="clip-analysis-error"
                className="bg-rose-950/40 border border-rose-800/60 p-2.5 rounded-lg flex items-center justify-between text-[11px] text-rose-200"
              >
                <div className="flex items-center space-x-1.5 truncate mr-2">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                  <span className="truncate" title={analysisError}>
                    {analysisError}
                  </span>
                </div>
                {onRetryAnalysis && (
                  <button
                    type="button"
                    onClick={onRetryAnalysis}
                    className="shrink-0 text-xs bg-rose-900/60 hover:bg-rose-800 text-rose-200 px-2 py-0.5 rounded border border-rose-700/50 transition font-medium"
                  >
                    Retry
                  </button>
                )}
              </div>
            )}

            {/* Upload Progress Bar */}
            {uploadProgress !== null &&
              uploadProgress !== undefined &&
              uploadProgress >= 0 &&
              uploadProgress < 100 && (
                <div className="space-y-1 bg-slate-950/70 p-2 rounded-lg border border-slate-800">
                  <div className="flex justify-between text-[10px] text-indigo-300 font-mono">
                    <span>Uploading clip to server...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-indigo-500 h-1.5 rounded-full transition-all duration-200"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

            {stagedClip.method === 'browser_capture' && (
              <div
                data-testid="staged-clip-capture-warning"
                className="bg-amber-950/40 border border-amber-800/60 p-2.5 rounded-lg space-y-1 text-[11px] text-amber-200"
              >
                <div className="flex items-center space-x-1.5 font-semibold text-amber-300">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                  <span>Experimental Capture Notice</span>
                </div>
                <p className="text-amber-200/90 leading-relaxed">
                  Trailing overshoot ({stagedClip.durationDeltaSeconds >= 0 ? '+' : ''}{stagedClip.durationDeltaSeconds.toFixed(2)}s) and unverified DTS. For timing-critical evidence in Whodunnit annotations, native FFmpeg extraction (Mode A) is recommended.
                </p>
              </div>
            )}

            {stagedClip.notes && (
              <p className="text-[11px] text-slate-300 italic">
                Note: {stagedClip.notes}
              </p>
            )}
          </div>

          {/* Action Callout */}
          <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
            <button
              type="button"
              disabled={isAnalyzing || isLimitsExceeded || !onAnalyzeClip}
              onClick={() => onAnalyzeClip && onAnalyzeClip(stagedClip)}
              data-testid="upload-to-qwen-btn"
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition flex items-center space-x-1.5 ${
                isAnalyzing
                  ? 'bg-indigo-950 text-indigo-300 border-indigo-700/60 cursor-wait'
                  : isLimitsExceeded || !onAnalyzeClip
                  ? 'bg-slate-800/80 text-slate-500 border-slate-700/60 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500 shadow'
              }`}
              title={
                isLimitsExceeded
                  ? 'Clip exceeds limits (max 200MB, max 120s)'
                  : 'Upload temporary clip and analyze with Qwen2.5-VL'
              }
            >
              {isAnalyzing ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-indigo-300/30 border-t-indigo-300 rounded-full animate-spin"></span>
                  <span>
                    {uploadProgress !== null &&
                    uploadProgress !== undefined &&
                    uploadProgress < 100
                      ? `Uploading clip ${uploadProgress}%...`
                      : analysisProgressText || 'Analyzing Clip with Qwen...'}
                  </span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Analyze Clip with Qwen</span>
                </>
              )}
            </button>
            <span className="text-[10px] text-slate-400 italic">
              {isLimitsExceeded
                ? 'Limit exceeded'
                : isAnalyzing
                ? 'Processing on GPU...'
                : 'Uploads short clip only'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
