import React, { useMemo, useRef, useState } from 'react';
import { Check, Copy, Download, FileVideo, Loader2, X } from 'lucide-react';
import { LocalVideoItem, StagedClipItem } from '../../shared/types';
import { formatTimestamp } from './timestampUtils';
import { createAnalysisWindows, formatWindowOutputName, MAX_UPLOADED_CLIP_BYTES, MAX_UPLOADED_CLIP_SECONDS } from './analysisWindows';
import { generateNativeBatchCommand, NativeExtractionMode, SupportedShell } from './nativeCommandGenerator';
import { measureVideoFileDuration } from './browserCaptureExtractor';

interface Props {
  isOpen: boolean;
  localVideo: LocalVideoItem;
  interval: { start: number; end: number; label?: string };
  onClose: () => void;
  onClipsPrepared: (clips: StagedClipItem[]) => void;
}

interface ImportedWindow {
  windowIndex: number;
  file: File;
  duration: number;
  objectUrl: string;
}

export const WindowedClipPreparationModal: React.FC<Props> = ({ isOpen, localVideo, interval, onClose, onClipsPrepared }) => {
  const [shell, setShell] = useState<SupportedShell>('powershell');
  const [mode, setMode] = useState<NativeExtractionMode>('frame_accurate');
  const [sourcePath, setSourcePath] = useState(localVideo.filename);
  const [imported, setImported] = useState<ImportedWindow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const importedRef = useRef<ImportedWindow[]>([]);
  const transferringRef = useRef(false);

  const windows = useMemo(() => createAnalysisWindows(interval.start, interval.end), [interval.start, interval.end]);
  const outputNames = useMemo(() => windows.map((window) => formatWindowOutputName(localVideo.filename, window)), [windows, localVideo.filename]);
  const generated = useMemo(() => generateNativeBatchCommand(shell, {
    sourceFilename: localVideo.filename,
    sourcePathPlaceholder: sourcePath,
    windows,
    outputFilenames: outputNames,
    mode,
  }), [shell, localVideo.filename, sourcePath, windows, outputNames, mode]);

  React.useEffect(() => { importedRef.current = imported; }, [imported]);
  React.useEffect(() => () => {
    if (!transferringRef.current) importedRef.current.forEach((item) => URL.revokeObjectURL(item.objectUrl));
  }, []);
  if (!isOpen) return null;

  const importFiles = async (files: FileList | null) => {
    if (!files) return;
    setChecking(true);
    setError(null);
    const next: ImportedWindow[] = [];
    const errors: string[] = [];
    const seen = new Set<number>();
    try {
      for (const file of Array.from(files)) {
        const match = file.name.match(/_w(\d{2})_/i);
        const index = match ? Number(match[1]) : NaN;
        const target = windows.find((window) => window.index === index);
        if (!target) {
          errors.push(`${file.name}: keep the generated _wNN_ window number in the filename.`);
          continue;
        }
        if (seen.has(index)) {
          errors.push(`Window ${String(index).padStart(2, '0')} was selected more than once.`);
          continue;
        }
        seen.add(index);
        if (file.size <= 0 || file.size > MAX_UPLOADED_CLIP_BYTES) {
          errors.push(`${file.name}: each uploaded window must be between 1 byte and 1 GB.`);
          continue;
        }
        const duration = await measureVideoFileDuration(file);
        if (!duration || duration > MAX_UPLOADED_CLIP_SECONDS) {
          errors.push(`${file.name}: could not read duration or it exceeds the 10-minute analysis limit.`);
          continue;
        }
        const expected = target.endSeconds - target.startSeconds;
        if (Math.abs(duration - expected) > 1.5) {
          errors.push(`${file.name}: measured duration differs from the selected window by more than 1.5 seconds.`);
          continue;
        }
        next.push({ windowIndex: index, file, duration, objectUrl: URL.createObjectURL(file) });
      }
    } finally {
      setChecking(false);
    }
    imported.forEach((item) => URL.revokeObjectURL(item.objectUrl));
    setImported(next.sort((a, b) => a.windowIndex - b.windowIndex));
    const missing = windows.filter((window) => !next.some((item) => item.windowIndex === window.index));
    if (errors.length || missing.length) {
      setError([
        ...errors,
        ...(missing.length ? [`Import all ${windows.length} generated windows. Missing: ${missing.map((w) => String(w.index).padStart(2, '0')).join(', ')}.`] : []),
      ].join(' '));
    }
  };

  const downloadScript = () => {
    const url = URL.createObjectURL(new Blob([generated.scriptContent], { type: 'text/plain;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `extract_${localVideo.filename.replace(/\.[^.]+$/, '')}_windows.${generated.scriptExtension}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const copyScript = async () => {
    await navigator.clipboard.writeText(generated.scriptContent);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const prepare = () => {
    if (imported.length !== windows.length) return;
    const staged = imported.map((item) => {
      const window = windows[item.windowIndex - 1];
      const expectedDuration = window.endSeconds - window.startSeconds;
      return {
        id: `window_${window.index}_${Date.now()}`,
        file: item.file,
        objectUrl: item.objectUrl,
        filename: item.file.name,
        sizeBytes: item.file.size,
        durationSeconds: item.duration,
        measuredDurationSeconds: item.duration,
        method: 'native_ffmpeg_assisted' as const,
        alignmentStatus: Math.abs(item.duration - expectedDuration) > 0.5 ? 'unverified' as const : 'user_confirmed' as const,
        userConfirmedAssociation: true,
        sourceVideoName: localVideo.filename,
        sourceVideoRef: localVideo.sourceInstanceId,
        sourceStartSeconds: window.startSeconds,
        sourceEndSeconds: window.endSeconds,
        sourceDurationSeconds: expectedDuration,
        durationDeltaSeconds: item.duration - expectedDuration,
        notes: interval.label ? `${interval.label} · window ${window.index}/${windows.length}` : `Analysis window ${window.index}/${windows.length}`,
        createdAt: new Date().toISOString(),
      } satisfies StagedClipItem;
    });
    transferringRef.current = true;
    onClipsPrepared(staged);
    onClose();
  };

  return (
    <div data-testid="windowed-preparation-modal" className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="windowed-prepare-title">
      <div className="w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl text-slate-100">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-800 bg-slate-900 px-6 py-4">
          <div>
            <h2 id="windowed-prepare-title" className="text-lg font-semibold">Prepare analysis windows</h2>
            <p className="mt-1 text-sm text-slate-400">{formatTimestamp(interval.start)}–{formatTimestamp(interval.end)} · {windows.length} overlapping clips · original stays local</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>

        <div className="grid gap-6 p-6 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="space-y-4">
            <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 text-sm text-indigo-100">
              Browsers cannot run native FFmpeg. Download and run the batch script beside your local recording, then import all generated clips here. Only these short clips are uploaded for analysis.
            </div>
            <label className="block text-xs font-medium text-slate-300">Local source path used by FFmpeg
              <input value={sourcePath} onChange={(event) => setSourcePath(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white" />
            </label>
            <div className="flex flex-wrap items-end gap-3">
              <label className="text-xs text-slate-400">Shell
                <select value={shell} onChange={(event) => setShell(event.target.value as SupportedShell)} className="mt-1 block rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
                  <option value="powershell">Windows PowerShell</option><option value="cmd">Windows CMD</option><option value="bash">Bash / macOS</option>
                </select>
              </label>
              <label className="text-xs text-slate-400">Extraction accuracy
                <select value={mode} onChange={(event) => setMode(event.target.value as NativeExtractionMode)} className="mt-1 block rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
                  <option value="frame_accurate">Frame-accurate re-encode (recommended)</option><option value="fast_copy">Fast keyframe copy (approximate)</option>
                </select>
              </label>
              <button onClick={downloadScript} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"><Download className="h-4 w-4" />Download batch script</button>
              <button onClick={copyScript} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700">{copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}{copied ? 'Copied' : 'Copy'}</button>
            </div>
            <ol className="max-h-64 space-y-2 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              {windows.map((window, index) => <li key={window.index} className="flex items-center justify-between gap-3 text-xs">
                <span className="font-mono text-slate-300">{String(index + 1).padStart(2, '0')} · {formatTimestamp(window.startSeconds)}–{formatTimestamp(window.endSeconds)}</span>
                <span className="truncate text-right text-slate-500">{outputNames[index]}</span>
              </li>)}
            </ol>
          </section>

          <section className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <h3 className="font-semibold">Import generated windows</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">Select every output file at once. Keep the generated <span className="font-mono text-slate-300">_wNN_</span> marker in each filename so CASTLE can map the clip to its source timestamps.</p>
              <input data-testid="windowed-files-input" ref={fileInputRef} type="file" multiple accept="video/mp4,video/*" className="hidden" onChange={(event) => importFiles(event.target.files)} />
              <button onClick={() => fileInputRef.current?.click()} disabled={checking} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-sm font-medium hover:bg-slate-700 disabled:opacity-50">
                {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileVideo className="h-4 w-4" />}{checking ? 'Checking media…' : `Select ${windows.length} window clips`}
              </button>
              <div className="mt-3 space-y-2">
                {windows.map((window) => {
                  const item = imported.find((candidate) => candidate.windowIndex === window.index);
                  return <div key={window.index} className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-slate-400">Window {String(window.index).padStart(2, '0')}</span>
                    {item ? <span className="truncate text-emerald-300">{item.file.name} · {(item.file.size / 1024 / 1024).toFixed(1)} MB</span> : <span className="text-slate-600">Not imported</span>}
                  </div>;
                })}
              </div>
              {error && <p role="alert" className="mt-3 rounded-lg border border-rose-800/60 bg-rose-950/50 p-3 text-xs text-rose-200">{error}</p>}
            </div>
            <div className="rounded-lg border border-slate-800 p-3 text-xs text-slate-400">Uploads are limited to 10 minutes and 1 GB.</div>
            <button onClick={prepare} disabled={checking || imported.length !== windows.length} className="w-full rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40">Prepare {windows.length} clips for analysis</button>
          </section>
        </div>
      </div>
    </div>
  );
};
