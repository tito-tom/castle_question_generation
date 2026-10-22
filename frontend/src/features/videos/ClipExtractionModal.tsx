import React, { useState, useRef, useEffect } from 'react';
import {
  X,
  Terminal,
  Upload,
  Video,
  Copy,
  Check,
  Download,
  AlertTriangle,
  Play,
  Pause,
  AlertCircle,
  FileVideo,
  Info,
  Clock,
  HardDrive,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import {
  LocalVideoItem,
  VideoIntervalSelection,
  StagedClipItem,
  formatFileSize,
} from '../../shared/types';
import {
  formatTimestamp,
  formatDuration,
} from './timestampUtils';
import {
  generateNativeCommand,
  SupportedShell,
  NativeExtractionMode,
} from './nativeCommandGenerator';
import {
  extractClipWithBrowserCapture,
  isBrowserCaptureSupported,
  measureVideoFileDuration,
  BrowserCaptureProgress,
} from './browserCaptureExtractor';

export interface ClipExtractionModalProps {
  isOpen: boolean;
  onClose: () => void;
  localVideo: LocalVideoItem;
  interval: { start: number; end: number; label?: string };
  onClipStaged: (stagedClip: StagedClipItem) => void;
}

export const ClipExtractionModal: React.FC<ClipExtractionModalProps> = ({
  isOpen,
  onClose,
  localVideo,
  interval,
  onClipStaged,
}) => {
  const [activeTab, setActiveTab] = useState<'mode_a' | 'mode_b' | 'mode_c'>('mode_a');

  // Mode A: Native FFmpeg state
  const [shell, setShell] = useState<SupportedShell>('powershell');
  const [nativeMode, setNativeMode] = useState<NativeExtractionMode>('frame_accurate');
  const [sourcePathInput, setSourcePathInput] = useState<string>(localVideo.filename);
  const [copied, setCopied] = useState<boolean>(false);

  // Mode B: Import state
  const [importedFile, setImportedFile] = useState<File | null>(null);
  const [importedPreviewUrl, setImportedPreviewUrl] = useState<string | null>(null);
  const [importedDuration, setImportedDuration] = useState<number>(0);
  const [importError, setImportError] = useState<string | null>(null);
  const stageInputRef = useRef<HTMLInputElement>(null);
  const directImportInputRef = useRef<HTMLInputElement>(null);

  // Mode C: Browser Capture state
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [captureProgress, setCaptureProgress] = useState<BrowserCaptureProgress | null>(null);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [capturedPreviewUrl, setCapturedPreviewUrl] = useState<string | null>(null);
  const [capturedDuration, setCapturedDuration] = useState<number>(0);
  const [capturedWallClockDuration, setCapturedWallClockDuration] = useState<number>(0);
  const [capturePlaybackRate, setCapturePlaybackRate] = useState<number>(1);
  const [captureWarning, setCaptureWarning] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Active source instance tracker for stale callback & resource isolation
  const activeSourceIdRef = useRef<string>(localVideo.sourceInstanceId);
  const importedPreviewUrlRef = useRef<string | null>(null);
  const capturedPreviewUrlRef = useRef<string | null>(null);

  useEffect(() => {
    importedPreviewUrlRef.current = importedPreviewUrl;
  }, [importedPreviewUrl]);

  useEffect(() => {
    capturedPreviewUrlRef.current = capturedPreviewUrl;
  }, [capturedPreviewUrl]);

  // Handle source video replacement or modal unmount/close
  useEffect(() => {
    if (activeSourceIdRef.current !== localVideo.sourceInstanceId) {
      activeSourceIdRef.current = localVideo.sourceInstanceId;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      if (importedPreviewUrlRef.current) {
        URL.revokeObjectURL(importedPreviewUrlRef.current);
        importedPreviewUrlRef.current = null;
      }
      if (capturedPreviewUrlRef.current) {
        URL.revokeObjectURL(capturedPreviewUrlRef.current);
        capturedPreviewUrlRef.current = null;
      }
      setImportedFile(null);
      setImportedPreviewUrl(null);
      setImportedDuration(0);
      setCapturedFile(null);
      setCapturedPreviewUrl(null);
      setCapturedDuration(0);
      setCapturedWallClockDuration(0);
      setCapturePlaybackRate(1);
      setIsCapturing(false);
      setCaptureProgress(null);
      setCaptureError(null);
      setCaptureWarning(null);
      setSourcePathInput(localVideo.filename);
    }
  }, [localVideo.sourceInstanceId, localVideo.filename]);

  // Cancel running capture and release preview if modal is closed
  useEffect(() => {
    if (!isOpen) {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setIsCapturing(false);
    }
  }, [isOpen]);

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      if (importedPreviewUrlRef.current) {
        URL.revokeObjectURL(importedPreviewUrlRef.current);
      }
      if (capturedPreviewUrlRef.current) {
        URL.revokeObjectURL(capturedPreviewUrlRef.current);
      }
    };
  }, []);

  if (!isOpen) return null;

  const durationTarget = Math.max(0.1, interval.end - interval.start);

  // Mode A Generated Command
  const generated = generateNativeCommand(shell, {
    sourceFilename: localVideo.filename,
    sourcePathPlaceholder: sourcePathInput,
    startSeconds: interval.start,
    endSeconds: interval.end,
    mode: nativeMode,
  });

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(generated.commandLine);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadScript = () => {
    const blob = new Blob([generated.scriptContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `extract_${generated.outputFilename.replace(/\.mp4$/, '')}.${generated.scriptExtension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Mode B: File Selection & Ingestion
  const handleSelectImportFile = (file: File) => {
    if (!file) return;
    if (file.size === 0) {
      setImportError('Selected file is empty (0 bytes).');
      return;
    }

    if (importedPreviewUrl) URL.revokeObjectURL(importedPreviewUrl);

    try {
      const url = URL.createObjectURL(file);
      setImportedFile(file);
      setImportedPreviewUrl(url);
      setImportError(null);
      // measure duration asynchronously without blocking user staging flow
      measureVideoFileDuration(file)
        .then((measuredDur) => {
          if (measuredDur > 0) {
            setImportedDuration(measuredDur);
          }
        })
        .catch(() => {});
    } catch {
      setImportError('Could not decode imported media file.');
    }
  };

  const handleConfirmImport = (method: 'native_ffmpeg_assisted' | 'direct_import') => {
    if (!importedFile) return;

    const delta = importedDuration > 0 ? importedDuration - durationTarget : 0;

    // Provenance Correction: Generating a command does not prove the clip was produced or frame-accurate.
    // Staged imported clips require user confirmation of association, and are marked 'user_confirmed',
    // 'approximate' (fast copy), or 'unverified' (duration mismatch), but NEVER 'verified'.
    let alignmentStatus: 'user_confirmed' | 'approximate' | 'unverified' = 'user_confirmed';
    if (method === 'native_ffmpeg_assisted') {
      if (nativeMode === 'fast_copy') {
        alignmentStatus = 'approximate';
      } else if (importedDuration > 0 && Math.abs(delta) > 0.5) {
        alignmentStatus = 'unverified';
      } else {
        alignmentStatus = 'user_confirmed';
      }
    } else {
      if (importedDuration > 0 && Math.abs(delta) > 0.5) {
        alignmentStatus = 'unverified';
      } else {
        alignmentStatus = 'user_confirmed';
      }
    }

    const stagedItem: StagedClipItem = {
      id: `staged_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      file: importedFile,
      objectUrl: importedPreviewUrl || URL.createObjectURL(importedFile),
      filename: importedFile.name,
      sizeBytes: importedFile.size,
      durationSeconds: importedDuration > 0 ? importedDuration : durationTarget,
      measuredDurationSeconds: importedDuration > 0 ? importedDuration : undefined,
      method,
      alignmentStatus,
      userConfirmedAssociation: true,
      sourceVideoName: localVideo.filename,
      sourceVideoRef: localVideo.sourceInstanceId,
      sourceStartSeconds: interval.start,
      sourceEndSeconds: interval.end,
      sourceDurationSeconds: durationTarget,
      durationDeltaSeconds: delta,
      notes: interval.label,
      createdAt: new Date().toISOString(),
    };

    // Detach imported preview so modal unmount does not revoke the staged clip's object URL
    importedPreviewUrlRef.current = null;
    setImportedPreviewUrl(null);
    onClipStaged(stagedItem);
    onClose();
  };

  // Mode C: Browser Capture Execution
  const handleStartCapture = async () => {
    const capturingSourceId = localVideo.sourceInstanceId;
    setIsCapturing(true);
    setCaptureError(null);
    setCaptureWarning(null);
    setCaptureProgress(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const result = await extractClipWithBrowserCapture(
        localVideo.file,
        interval.start,
        interval.end,
        setCaptureProgress,
        controller.signal
      );

      // Stale callback protection: if source changed while recording, discard result
      if (activeSourceIdRef.current !== capturingSourceId || controller.signal.aborted || !isOpen) {
        URL.revokeObjectURL(result.objectUrl);
        return;
      }

      if (capturedPreviewUrlRef.current && capturedPreviewUrlRef.current !== result.objectUrl) {
        URL.revokeObjectURL(capturedPreviewUrlRef.current);
      }
      capturedPreviewUrlRef.current = result.objectUrl;
      setCapturedFile(result.file);
      setCapturedPreviewUrl(result.objectUrl);
      setCapturedDuration(result.actualDurationSeconds);
      setCapturedWallClockDuration(result.captureWallClockSeconds);
      setCapturePlaybackRate(result.capturePlaybackRate);
      if (result.warningMessage) {
        setCaptureWarning(result.warningMessage);
      }
    } catch (err: any) {
      if (activeSourceIdRef.current !== capturingSourceId || !isOpen) {
        return;
      }
      if (err.message && err.message.includes('cancelled')) {
        setCaptureError('Capture was cancelled.');
      } else {
        setCaptureError(err.message || 'Browser capture failed.');
      }
    } finally {
      if (activeSourceIdRef.current === capturingSourceId) {
        setIsCapturing(false);
        abortControllerRef.current = null;
      }
    }
  };

  const handleCancelCapture = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleConfirmCapturedClip = () => {
    if (!capturedFile || !capturedPreviewUrl) return;

    const delta = capturedDuration - durationTarget;
    const stagedItem: StagedClipItem = {
      id: `staged_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      file: capturedFile,
      objectUrl: capturedPreviewUrl,
      filename: capturedFile.name,
      sizeBytes: capturedFile.size,
      durationSeconds: capturedDuration,
      measuredDurationSeconds: capturedDuration,
      method: 'browser_capture',
      alignmentStatus: 'approximate',
      userConfirmedAssociation: true,
      sourceVideoName: localVideo.filename,
      sourceVideoRef: localVideo.sourceInstanceId,
      sourceStartSeconds: interval.start,
      sourceEndSeconds: interval.end,
      sourceDurationSeconds: durationTarget,
      durationDeltaSeconds: delta,
      captureWallClockSeconds: capturedWallClockDuration,
      capturePlaybackRate: capturePlaybackRate,
      notes: interval.label ? `${interval.label} (Browser Capture)` : 'Browser Capture',
      createdAt: new Date().toISOString(),
    };

    // Detach captured preview so modal cleanup does not revoke staged object URL
    // Transfer ownership synchronously before parent closes/unmounts this modal.
    capturedPreviewUrlRef.current = null;
    setCapturedPreviewUrl(null);
    onClipStaged(stagedItem);
    onClose();
  };

  return (
    <div
      data-testid="clip-extraction-modal"
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
    >
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col my-8">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="p-1.5 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
                <Video className="w-4 h-4" />
              </span>
              <h3 className="text-sm font-bold text-white">Extract Local Video Clip</h3>
            </div>
            <p className="text-xs text-slate-400 flex items-center space-x-2">
              <span>{localVideo.filename}</span>
              <span>•</span>
              <span className="font-mono text-indigo-300">
                {formatTimestamp(interval.start)} → {formatTimestamp(interval.end)} ({formatDuration(durationTarget)})
              </span>
            </p>
          </div>

          <button
            onClick={onClose}
            data-testid="close-extraction-modal-btn"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-5 pt-2 space-x-2">
          <button
            onClick={() => setActiveTab('mode_a')}
            data-testid="tab-mode-a"
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition border-b-2 flex items-center space-x-2 ${
              activeTab === 'mode_a'
                ? 'border-indigo-500 text-indigo-400 bg-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Native FFmpeg (Recommended)</span>
          </button>

          <button
            onClick={() => setActiveTab('mode_b')}
            data-testid="tab-mode-b"
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition border-b-2 flex items-center space-x-2 ${
              activeTab === 'mode_b'
                ? 'border-indigo-500 text-indigo-400 bg-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import Existing Clip</span>
          </button>

          <button
            onClick={() => setActiveTab('mode_c')}
            data-testid="tab-mode-c"
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition border-b-2 flex items-center space-x-2 ${
              activeTab === 'mode_c'
                ? 'border-amber-500 text-amber-400 bg-slate-900'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Browser Capture (Experimental)</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* TAB MODE A: Native FFmpeg Assisted Extraction */}
          {activeTab === 'mode_a' && (
            <div className="space-y-4 text-xs">
              <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-xl flex items-start space-x-2.5 text-slate-300">
                <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <div className="space-y-1 leading-relaxed">
                  <p className="font-medium text-white">Recommended for Timestamp-Sensitive Annotations</p>
                  <p className="text-slate-400">
                    Run this command in your terminal to extract the clip locally using your computer&apos;s native FFmpeg.
                    The original video stays on your drive. Once generated, drop the resulting file below to stage it!
                  </p>
                </div>
              </div>

              {/* Shell & Mode Selectors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-400">Target Shell</label>
                  <div className="flex space-x-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
                    <button
                      type="button"
                      onClick={() => setShell('powershell')}
                      data-testid="shell-powershell-btn"
                      className={`flex-1 py-1 text-center rounded text-[11px] font-medium transition ${
                        shell === 'powershell' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      PowerShell
                    </button>
                    <button
                      type="button"
                      onClick={() => setShell('cmd')}
                      data-testid="shell-cmd-btn"
                      className={`flex-1 py-1 text-center rounded text-[11px] font-medium transition ${
                        shell === 'cmd' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      CMD
                    </button>
                    <button
                      type="button"
                      onClick={() => setShell('bash')}
                      data-testid="shell-bash-btn"
                      className={`flex-1 py-1 text-center rounded text-[11px] font-medium transition ${
                        shell === 'bash' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Bash
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-slate-400">Extraction Quality Mode</label>
                  <div className="flex space-x-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
                    <button
                      type="button"
                      onClick={() => setNativeMode('frame_accurate')}
                      data-testid="mode-frame-accurate-btn"
                      className={`flex-1 py-1 text-center rounded text-[11px] font-medium transition ${
                        nativeMode === 'frame_accurate' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Frame-Accurate
                    </button>
                    <button
                      type="button"
                      onClick={() => setNativeMode('fast_copy')}
                      data-testid="mode-fast-copy-btn"
                      className={`flex-1 py-1 text-center rounded text-[11px] font-medium transition ${
                        nativeMode === 'fast_copy' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Fast Copy (GOP Snap)
                    </button>
                  </div>
                </div>
              </div>

              {/* Keyframe warning for fast copy mode */}
              {generated.keyframeWarning && (
                <div
                  data-testid="keyframe-warning-notice"
                  className="bg-amber-950/40 border border-amber-800/50 p-2.5 rounded-lg text-amber-300 text-xs flex items-center space-x-2"
                >
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{generated.keyframeWarning}</span>
                </div>
              )}

              {/* Source path input */}
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-400 flex items-center justify-between">
                  <span>Input File Path / Name</span>
                  <span className="text-[10px] text-slate-500 font-normal">
                    (Browsers cannot access full local paths directly)
                  </span>
                </label>
                <input
                  type="text"
                  value={sourcePathInput}
                  onChange={(e) => setSourcePathInput(e.target.value)}
                  placeholder="e.g. D:\Videos\kitchen_8_day_1.mp4"
                  data-testid="source-path-input"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Command Code Block */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-400">Generated Command</span>
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={handleCopyCommand}
                      data-testid="copy-command-btn"
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded border border-slate-700 transition flex items-center space-x-1"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Copied!' : 'Copy Command'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleDownloadScript}
                      data-testid="download-script-btn"
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition flex items-center space-x-1"
                    >
                      <Download className="w-3.5 h-3.5 text-slate-400" />
                      <span>Download Script</span>
                    </button>
                  </div>
                </div>

                <div
                  data-testid="command-preview-box"
                  className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-xs text-emerald-300 break-all select-all leading-relaxed shadow-inner"
                >
                  {generated.commandLine}
                </div>
              </div>

              {/* Dropzone for generated file */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <span className="text-xs font-semibold text-white block">
                  Step 2: Stage Extracted Clip
                </span>
                <p className="text-[11px] text-slate-400">
                  After running the command above, select or drop the generated file here to stage it for annotation.
                </p>

                <div
                  onClick={() => stageInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                      handleSelectImportFile(e.dataTransfer.files[0]);
                    }
                  }}
                  data-testid="stage-dropzone"
                  className="border-2 border-dashed border-slate-700 hover:border-indigo-500/80 rounded-xl p-4 text-center cursor-pointer transition bg-slate-950/40 hover:bg-slate-950/70"
                >
                  <input
                    ref={stageInputRef}
                    type="file"
                    accept="video/*,.mp4,.webm,.mov"
                    className="hidden"
                    data-testid="stage-clip-file-input"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleSelectImportFile(e.target.files[0]);
                      }
                    }}
                  />
                  {importedFile ? (
                    <div className="flex items-center justify-center space-x-2 text-emerald-400 font-medium text-xs">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Ready to stage: {importedFile.name} ({formatFileSize(importedFile.size)})</span>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <Upload className="w-5 h-5 text-indigo-400 mx-auto" />
                      <p className="text-xs text-slate-300 font-medium">Click to select or drag and drop extracted file</p>
                      <p className="text-[10px] text-slate-500">Expected: {generated.outputFilename}</p>
                    </div>
                  )}
                </div>

                {importedFile && (
                  <button
                    type="button"
                    onClick={() => handleConfirmImport('native_ffmpeg_assisted')}
                    data-testid="confirm-stage-ffmpeg-btn"
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg shadow transition flex items-center justify-center space-x-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Confirm & Stage Extracted Clip</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* TAB MODE B: Direct Short-Clip Import */}
          {activeTab === 'mode_b' && (
            <div className="space-y-4 text-xs">
              <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-xl flex items-start space-x-2.5 text-slate-300">
                <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <div className="space-y-1 leading-relaxed">
                  <p className="font-medium text-white">Import an Already-Extracted Short Clip</p>
                  <p className="text-slate-400">
                    If you have already trimmed a clip from this recording (e.g. using any external video editor or earlier FFmpeg run),
                    import it directly. Its temporal alignment will be marked as <strong className="text-indigo-300">user-confirmed</strong>.
                  </p>
                </div>
              </div>

              <div
                onClick={() => directImportInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleSelectImportFile(e.dataTransfer.files[0]);
                  }
                }}
                data-testid="import-clip-dropzone"
                className="border-2 border-dashed border-slate-700 hover:border-indigo-500/80 rounded-xl p-6 text-center cursor-pointer transition bg-slate-950/50 hover:bg-slate-950/80 relative"
              >
                <input
                  ref={directImportInputRef}
                  type="file"
                  accept="video/*,.mp4,.webm,.mov"
                  className="hidden"
                  data-testid="import-clip-file-input"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleSelectImportFile(e.target.files[0]);
                    }
                  }}
                />
                <FileVideo className="w-8 h-8 text-indigo-400 mx-auto mb-2" />
                <p className="text-xs font-medium text-slate-200">Drop your short video clip here, or click to browse</p>
                <p className="text-[11px] text-slate-500 mt-1">Supports MP4, WebM, MOV</p>
              </div>

              {importError && (
                <div className="bg-rose-950/40 border border-rose-800 p-2.5 rounded-lg text-rose-300 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{importError}</span>
                </div>
              )}

              {importedFile && importedPreviewUrl && (
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-white">{importedFile.name}</span>
                      <span className="text-slate-500 ml-2 font-mono">({formatFileSize(importedFile.size)})</span>
                    </div>
                    <span className="font-mono text-emerald-400">
                      Duration: {importedDuration.toFixed(1)}s (Target: {durationTarget.toFixed(1)}s)
                    </span>
                  </div>

                  {Math.abs(importedDuration - durationTarget) > 2.0 && (
                    <div className="text-[11px] text-amber-300 bg-amber-950/30 border border-amber-800/40 p-2 rounded-lg flex items-center space-x-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>
                        Imported duration ({importedDuration.toFixed(1)}s) differs from interval target ({durationTarget.toFixed(1)}s).
                        Alignment will be recorded as user-confirmed.
                      </span>
                    </div>
                  )}

                  <div className="aspect-video bg-black rounded-lg overflow-hidden border border-slate-800">
                    <video src={importedPreviewUrl} controls className="w-full h-full object-contain" />
                  </div>

                  <button
                    type="button"
                    onClick={() => handleConfirmImport('direct_import')}
                    data-testid="confirm-direct-import-btn"
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg shadow transition flex items-center justify-center space-x-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Stage Imported Clip</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB MODE C: Experimental Browser Capture */}
          {activeTab === 'mode_c' && (
            <div className="space-y-4 text-xs">
              <div
                data-testid="browser-capture-warning"
                className="bg-amber-950/40 border border-amber-800/60 p-3.5 rounded-xl space-y-2 text-amber-200"
              >
                <div className="flex items-center space-x-2 font-semibold text-amber-300">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>Experimental Feature Notice</span>
                </div>
                <ul className="list-disc list-inside space-y-1 text-[11px] text-amber-300/90 leading-relaxed">
                  <li><strong>Real-Time Duration:</strong> Capture plays the interval in real time (~{durationTarget.toFixed(0)} seconds).</li>
                  <li><strong>Tab Visibility:</strong> Keep this tab active! Hiding or minimizing the window freezes video rendering.</li>
                  <li><strong>Known Limitations:</strong> Browser MediaRecorder introduces ~0.6–1.1s duration overshoot and non-monotonic DTS warnings.</li>
                  <li><strong>Recommendation:</strong> Native FFmpeg is strongly recommended for strict frame accuracy and instant execution.</li>
                </ul>
              </div>

              {!isBrowserCaptureSupported() ? (
                <div className="bg-rose-950/40 border border-rose-800 p-3 rounded-lg text-rose-300 text-xs">
                  captureStream or MediaRecorder is not supported in this browser. Please use Mode A or Mode B.
                </div>
              ) : (
                <div className="space-y-3">
                  {!isCapturing && !capturedFile && (
                    <>
                      {durationTarget > 120 && (
                        <div className="bg-rose-950/40 border border-rose-800 p-3 rounded-lg text-rose-200" data-testid="capture-limit-warning">
                          This {durationTarget.toFixed(1)} second interval exceeds the current 120 second Qwen limit. Choose a shorter interval; browser capture will not start.
                        </div>
                      )}
                      <button
                        type="button"
                        onClick={handleStartCapture}
                        disabled={durationTarget > 120}
                        data-testid="start-browser-capture-btn"
                        className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-700 disabled:text-slate-400 text-white text-xs font-bold rounded-xl shadow transition flex items-center justify-center space-x-2"
                      >
                        <Play className="w-4 h-4" />
                        <span>Start In-Browser Capture ({durationTarget.toFixed(0)}s Realtime)</span>
                      </button>
                    </>
                  )}

                  {isCapturing && (
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-white font-medium flex items-center space-x-2">
                          <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
                          <span>{captureProgress?.statusText || 'Capturing playback stream...'}</span>
                        </span>
                        <span className="font-mono text-amber-300">{captureProgress?.percent || 0}%</span>
                      </div>

                      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-500 transition-all duration-150"
                          style={{ width: `${captureProgress?.percent || 0}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        <span className="text-[10px] text-slate-500 font-mono">
                          {captureProgress ? `${formatTimestamp(captureProgress.currentTime)} / ${formatTimestamp(interval.end)}` : ''}
                        </span>

                        <button
                          type="button"
                          onClick={handleCancelCapture}
                          data-testid="cancel-capture-btn"
                          className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-rose-300 rounded border border-slate-700 text-xs transition"
                        >
                          Cancel Capture
                        </button>
                      </div>
                    </div>
                  )}

                  {captureError && (
                    <div className="bg-rose-950/40 border border-rose-800 p-2.5 rounded-lg text-rose-300 text-xs flex items-center space-x-2">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>{captureError}</span>
                    </div>
                  )}

                  {captureWarning && (
                    <div
                      data-testid="browser-capture-overshoot-warning"
                      className="bg-amber-950/40 border border-amber-800 p-2.5 rounded-lg text-amber-300 text-xs flex items-center space-x-2"
                    >
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>{captureWarning}</span>
                    </div>
                  )}

                  {capturedFile && capturedPreviewUrl && !isCapturing && (
                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-3" data-testid="capture-ready-for-staging">
                      <div className="flex items-center justify-between text-xs">
                        <div>
                          <span className="font-semibold text-white">{capturedFile.name}</span>
                          <span className="text-slate-500 ml-2 font-mono">({formatFileSize(capturedFile.size)})</span>
                        </div>
                          <span className="font-mono text-emerald-400">
                          Validated {capturedFile.type} · Media: {capturedDuration.toFixed(2)}s · Recorder wall time: {capturedWallClockDuration.toFixed(2)}s · Playback rate: {capturePlaybackRate.toFixed(2)}x · Target: {durationTarget.toFixed(2)}s (Delta: {capturedDuration - durationTarget >= 0 ? '+' : ''}{(capturedDuration - durationTarget).toFixed(2)}s)
                        </span>
                      </div>

                      {/* Explicit experimental warning & recommendation */}
                      <div className="bg-amber-950/40 border border-amber-800/60 p-2.5 rounded-lg space-y-1 text-[11px] text-amber-200" data-testid="capture-result-warning">
                        <div className="flex items-center space-x-1.5 font-semibold text-amber-300">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                          <span>Experimental Browser Capture Warning</span>
                        </div>
                        <p className="text-amber-200/90 leading-relaxed">
                          Requested: <strong>{durationTarget.toFixed(2)}s</strong> • Measured: <strong>{capturedDuration.toFixed(2)}s</strong> • Difference: <strong>{capturedDuration - durationTarget >= 0 ? '+' : ''}{(capturedDuration - durationTarget).toFixed(2)}s</strong>.
                        </p>
                        <p className="text-amber-300/80 leading-relaxed">
                          HTML video metadata checks do not verify decoding timestamp (DTS/PTS) integrity. For timing-critical evidence in Whodunnit annotations, native FFmpeg extraction (Mode A) is strongly recommended.
                        </p>
                      </div>

                      <div className="aspect-video bg-black rounded-lg overflow-hidden border border-slate-800">
                        <video src={capturedPreviewUrl} controls className="w-full h-full object-contain" />
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={handleConfirmCapturedClip}
                          data-testid="confirm-browser-capture-btn"
                          className="flex-1 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-lg shadow transition flex items-center justify-center space-x-1.5"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Stage Captured Clip</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            if (capturedPreviewUrlRef.current) URL.revokeObjectURL(capturedPreviewUrlRef.current);
                            capturedPreviewUrlRef.current = null;
                            setCapturedFile(null);
                            setCapturedPreviewUrl(null);
                            setCapturedDuration(0);
                            setCapturedWallClockDuration(0);
                            setCapturePlaybackRate(1);
                          }}
                          className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
                        >
                          Discard
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
