import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Film,
  FileVideo,
  HardDrive,
  X,
  AlertCircle,
} from 'lucide-react';
import { api } from './shared/api/client';
import {
  VideoAnalysis,
  VideoItem,
  LocalVideoItem,
  VideoIntervalSelection,
  StagedClipItem,
  formatFileSize,
} from './shared/types';
import { Header } from './shared/components/Header';
import { VideoPlayer, VideoSeekRequest } from './features/videos/VideoPlayer';
import { useLocalVideo } from './features/videos/useLocalVideo';
import { ClipSelectionPanel } from './features/videos/ClipSelectionPanel';
import { ClipExtractionModal } from './features/videos/ClipExtractionModal';
import { StagedClipCard } from './features/videos/StagedClipCard';
import { MAX_SOURCE_INTERVAL_SECONDS } from './features/videos/analysisWindows';
import { TimelineView } from './features/video-understanding/TimelineView';
import { QuestionGenerationWorkspace } from './features/question-generation/QuestionGenerationWorkspace';

export const App: React.FC = () => {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoItem | null>(null);
  const [activeSourceType, setActiveSourceType] = useState<'local' | 'server' | null>(null);
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);

  const [currentTime, setCurrentTime] = useState(0);
  const [seekTime, setSeekTime] = useState<number | null>(null);
  const [seekRequest, setSeekRequest] = useState<VideoSeekRequest | null>(null);
  const [activeInterval, setActiveInterval] = useState<{ start: number; end: number } | null>(null);

  // Client-side local video interval selections and duration
  const [localSelections, setLocalSelections] = useState<VideoIntervalSelection[]>([]);
  const [localVideoDuration, setLocalVideoDuration] = useState<number>(0);

  // Staged extracted short clip & extraction modal state
  const [stagedClip, setStagedClip] = useState<StagedClipItem | null>(null);
  const [uploadedClipMetadata, setUploadedClipMetadata] = useState<(VideoItem & { is_temporary?: boolean; session_id?: string; session_token?: string }) | null>(null);
  const [isExtractionOpen, setIsExtractionOpen] = useState(false);
  const [extractionTargetInterval, setExtractionTargetInterval] = useState<{
    start: number;
    end: number;
    label?: string;
  } | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingQuestions, setIsGeneratingQuestions] = useState(false);
  const [activeTab, setActiveTab] = useState<'understanding' | 'questions'>('understanding');

  // Staged clip temporary upload & Qwen video understanding state
  const [isClipAnalyzing, setIsClipAnalyzing] = useState(false);
  const [clipUploadProgress, setClipUploadProgress] = useState<number | null>(null);
  const [clipAnalysisProgressText, setClipAnalysisProgressText] = useState<string>('');
  const [clipAnalysisError, setClipAnalysisError] = useState<string | null>(null);
  const activeClipJobRef = useRef<{ cancelled: boolean }>({ cancelled: false });

  // Local-First video hook: keeps File in memory, creates/revokes object URLs, zero network upload
  const localVideoRef = useRef<LocalVideoItem | null>(null);
  const selectedVideoRef = useRef<VideoItem | null>(null);
  const activeSourceTypeRef = useRef<'local' | 'server' | null>(null);

  const {
    localVideo,
    error: localVideoError,
    selectFile,
    clearLocalVideo,
    openFileDialog,
    fileInputRef,
  } = useLocalVideo((item: LocalVideoItem) => {
    // Cancel any active clip job
    activeClipJobRef.current.cancelled = true;
    activeClipJobRef.current = { cancelled: false };
    setIsClipAnalyzing(false);
    setClipUploadProgress(null);
    setClipAnalysisProgressText('');
    setClipAnalysisError(null);

    // When a local video is chosen, switch active source to local immediately
    localVideoRef.current = item;
    activeSourceTypeRef.current = 'local';
    setActiveSourceType('local');
    setUploadedClipMetadata(null);
    setAnalysis(null);
    setActiveInterval(null);
    setSeekTime(null);
    setSeekRequest(null);
    setCurrentTime(0);
    setLocalSelections([]); // Invalidate previous selections on file change
    setLocalVideoDuration(0);

    // Invalidate and cleanup any previous staged clip
    setStagedClip((prev) => {
      if (prev) URL.revokeObjectURL(prev.objectUrl);
      return null;
    });
  });

  // Keep refs in sync with state
  useEffect(() => {
    localVideoRef.current = localVideo;
  }, [localVideo]);

  useEffect(() => {
    selectedVideoRef.current = selectedVideo;
  }, [selectedVideo]);

  useEffect(() => {
    activeSourceTypeRef.current = activeSourceType;
  }, [activeSourceType]);

  // Load server videos on mount
  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    try {
      const res = await api.getVideos();
      setVideos(res.videos);
      if (
        res.videos.length > 0 &&
        !selectedVideoRef.current &&
        !localVideoRef.current &&
        activeSourceTypeRef.current !== 'local'
      ) {
        handleSelectServerVideo(res.videos[0]);
      }
    } catch (err) {
      console.error('Failed to load videos', err);
    }
  };

  const handleSelectServerVideo = async (video: VideoItem) => {
    activeClipJobRef.current.cancelled = true;
    activeClipJobRef.current = { cancelled: false };
    setIsClipAnalyzing(false);
    setClipUploadProgress(null);
    setClipAnalysisProgressText('');
    setClipAnalysisError(null);

    if (stagedClip) URL.revokeObjectURL(stagedClip.objectUrl);
    setStagedClip(null);

    setSelectedVideo(video);
    setActiveSourceType('server');
    setUploadedClipMetadata(null);
    setAnalysis(null);
    setActiveInterval(null);
    setSeekTime(null);
    setSeekRequest(null);
    setCurrentTime(0);

    // Try loading analysis for this server video
    try {
      const an = await api.getAnalysis(video.video_id);
      setAnalysis(an);
    } catch {
      // Analysis doesn't exist yet for this video
    }
  };

  const handleSelectLocalVideo = () => {
    if (localVideo) {
      setActiveSourceType('local');
      setAnalysis(null);
      setActiveInterval(null);
      setSeekTime(null);
      setSeekRequest(null);
      setCurrentTime(0);
    } else {
      openFileDialog();
    }
  };

  const handleClearLocal = () => {
    activeClipJobRef.current.cancelled = true;
    activeClipJobRef.current = { cancelled: false };
    setIsClipAnalyzing(false);
    setClipUploadProgress(null);
    setClipAnalysisProgressText('');
    setClipAnalysisError(null);

    if (stagedClip) {
      URL.revokeObjectURL(stagedClip.objectUrl);
      setStagedClip(null);
    }
    clearLocalVideo();
    setLocalSelections([]);
    setActiveInterval(null);
    setSeekTime(null);
    setSeekRequest(null);
    setCurrentTime(0);
    setLocalVideoDuration(0);
    if (videos.length > 0) {
      handleSelectServerVideo(videos[0]);
    } else {
      setSelectedVideo(null);
      setActiveSourceType(null);
    }
  };

  // Interval extraction handlers
  const handleOpenExtraction = (interval: { start: number; end: number; label?: string }) => {
    if (interval.end - interval.start > MAX_SOURCE_INTERVAL_SECONDS) return;
    setExtractionTargetInterval(interval);
    setIsExtractionOpen(true);
  };

  const handleClipStaged = (clip: StagedClipItem) => {
    activeClipJobRef.current.cancelled = true;
    activeClipJobRef.current = { cancelled: false };
    setIsClipAnalyzing(false);
    setClipUploadProgress(null);
    setClipAnalysisProgressText('');
    setClipAnalysisError(null);
    setAnalysis(null);
    setUploadedClipMetadata(null);

    if (stagedClip && stagedClip.objectUrl !== clip.objectUrl) {
      URL.revokeObjectURL(stagedClip.objectUrl);
    }
    setStagedClip(clip);
  };

  const handleClearStagedClip = () => {
    activeClipJobRef.current.cancelled = true;
    activeClipJobRef.current = { cancelled: false };
    setIsClipAnalyzing(false);
    setClipUploadProgress(null);
    setClipAnalysisProgressText('');
    setClipAnalysisError(null);

    if (stagedClip) {
      URL.revokeObjectURL(stagedClip.objectUrl);
    }
    setStagedClip(null);
  };

  // Upload and analyze the one extracted interval clip.
  const handleAnalyzeStagedClip = async (clipToAnalyze: StagedClipItem) => {
    if (activeSourceType !== 'local' || !clipToAnalyze || isClipAnalyzing) return;
    if (clipToAnalyze.durationSeconds > MAX_SOURCE_INTERVAL_SECONDS) {
      setClipAnalysisError('Selected clip exceeds the 10-minute analysis limit.');
      return;
    }
    if (clipToAnalyze.sizeBytes > 1024 * 1024 * 1024) {
      setClipAnalysisError('Selected clip exceeds the 1 GB upload limit.');
      return;
    }

    // Invalidate any previous running poll
    activeClipJobRef.current.cancelled = true;
    const currentJob = { cancelled: false };
    activeClipJobRef.current = currentJob;

    setIsClipAnalyzing(true);
    setClipUploadProgress(0);
    setClipAnalysisProgressText('Uploading clip...');
    setClipAnalysisError(null);
    let uploadedVideoId: string | null = null;
    let jobWasSubmitted = false;

    try {
      // 1. Upload ONLY the short clip (never the 1.28 GB original local recording)
      const uploadedClip = await api.uploadTemporaryClip(
        clipToAnalyze.file,
        {
          sourceFilename: clipToAnalyze.sourceVideoName,
          sourceVideoRef: clipToAnalyze.sourceVideoRef,
          sourceStartSeconds: clipToAnalyze.sourceStartSeconds,
          sourceEndSeconds: clipToAnalyze.sourceEndSeconds,
          sourceDurationSeconds: clipToAnalyze.sourceDurationSeconds,
          extractionMethod: clipToAnalyze.method,
          alignmentStatus: clipToAnalyze.alignmentStatus,
          userConfirmed: clipToAnalyze.userConfirmedAssociation,
        },
        (pct: number) => {
          if (!currentJob.cancelled) {
            setClipUploadProgress(pct);
          }
        }
      );
      uploadedVideoId = uploadedClip.video_id;

      if (currentJob.cancelled) {
        await api.deleteTemporaryClip(uploadedClip.video_id).catch(() => undefined);
        return;
      }

      setClipUploadProgress(null);
      setClipAnalysisProgressText('Submitting analysis...');

      // 2. Submit video understanding job
      const { job_id } = await api.submitVideoUnderstanding(uploadedClip.video_id, 2.0);
      jobWasSubmitted = true;

      if (currentJob.cancelled) return;

      setClipAnalysisProgressText('Analyzing selected clip...');

      // 3. Poll job until finished
      const finishedJob = await api.pollJobUntilFinished(job_id);

      if (currentJob.cancelled) return;

      if (finishedJob.status === 'completed' && finishedJob.result_id) {
        setUploadedClipMetadata(uploadedClip);
        const loadedAnalysis = await api.getAnalysis(finishedJob.result_id);
        if (currentJob.cancelled) return;

        setAnalysis(loadedAnalysis);

        // Switch to timeline view so user immediately sees results
        setActiveTab('understanding');
        setClipAnalysisProgressText('');
      } else if (finishedJob.status === 'failed') {
        throw new Error(finishedJob.error_message || 'Video understanding failed');
      }
    } catch (err: any) {
      if (uploadedVideoId && !jobWasSubmitted) {
        await api.deleteTemporaryClip(uploadedVideoId).catch(() => undefined);
      }
      if (!currentJob.cancelled) {
        console.error('Clip analysis failed', err);
        setClipAnalysisError(err.message || 'Failed to analyze selected clip');
      }
    } finally {
      if (!currentJob.cancelled) {
        setIsClipAnalyzing(false);
        setClipUploadProgress(null);
      }
    }
  };

  // Interval selection handlers
  const handleJumpTo = (time: number, autoPlay: boolean = false) => {
    setSeekRequest({ time, autoPlay, id: Date.now() });
    setSeekTime(time);
  };

  const handlePreviewInterval = (interval: { start: number; end: number }) => {
    setActiveInterval(interval);
    setSeekRequest({ time: interval.start, autoPlay: true, id: Date.now() });
    setSeekTime(interval.start);
  };

  const handleAddSelection = (selection: VideoIntervalSelection) => {
    setLocalSelections((prev) => [...prev, selection]);
    setActiveInterval({ start: selection.startSeconds, end: selection.endSeconds });
  };

  const handleUpdateSelection = (selection: VideoIntervalSelection) => {
    setLocalSelections((prev) =>
      prev.map((s) => (s.id === selection.id ? selection : s))
    );
    setActiveInterval({ start: selection.startSeconds, end: selection.endSeconds });
  };

  const handleRemoveSelection = (id: string) => {
    setLocalSelections((prev) => prev.filter((s) => s.id !== id));
    if (
      activeInterval &&
      localSelections.some(
        (s) =>
          s.id === id &&
          Math.abs(s.startSeconds - activeInterval.start) < 0.05 &&
          Math.abs(s.endSeconds - activeInterval.end) < 0.05
      )
    ) {
      setActiveInterval(null);
    }
  };

  const handleRunVideoUnderstanding = async () => {
    if (!selectedVideo || activeSourceType !== 'server') return;
    setIsAnalyzing(true);

    try {
      const { job_id } = await api.submitVideoUnderstanding(selectedVideo.video_id);
      const finishedJob = await api.pollJobUntilFinished(job_id);

      if (finishedJob.status === 'completed' && finishedJob.result_id) {
        const loadedAnalysis = await api.getAnalysis(finishedJob.result_id);
        setAnalysis(loadedAnalysis);

      }
    } catch (err) {
      console.error('Video understanding failed', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateQuestions = async (criteriaText: string) => {
    const targetDuration =
      activeSourceType === 'server'
        ? (selectedVideo?.duration_seconds || 30.0)
        : (uploadedClipMetadata?.duration_seconds || stagedClip?.durationSeconds || (analysis?.source_start_seconds != null && analysis?.source_end_seconds != null ? analysis.source_end_seconds - analysis.source_start_seconds : 30.0));

    if (!analysis) throw new Error('Run video understanding before generating questions.');
    setIsGeneratingQuestions(true);

    try {
      const { job_id } = await api.submitQuestionGeneration(
        analysis.analysis_id,
        targetDuration,
        5,
        criteriaText
      );
      const finishedJob = await api.pollJobUntilFinished(job_id);

      if (finishedJob.status === 'completed' && finishedJob.result_id) {
        return await api.getQuestionGeneration(finishedJob.result_id);
      }
      throw new Error(finishedJob.error_message || 'Question generation did not complete.');
    } catch (err) {
      throw err instanceof Error ? err : new Error('Question generation failed.');
    } finally {
      setIsGeneratingQuestions(false);
    }
  };

  const handleSeekInterval = (interval: { start: number; end: number }) => {
    setActiveInterval(interval);
    setSeekTime(interval.start);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Hidden browser file picker for local video selection */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            selectFile(file);
          }
        }}
        accept="video/mp4,video/webm,video/ogg,video/quicktime,video/*"
        className="hidden"
        data-testid="local-video-file-input"
      />

      <Header />

      <main className="flex-1 max-w-screen-2xl w-full mx-auto p-5 lg:p-7 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Local capture and interval controls stay beside the prominent player. */}
        <div className="lg:col-span-7 flex flex-col space-y-4">
          {/* Video Selector & Source Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Video Library
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={openFileDialog}
                  className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 rounded-lg font-medium flex items-center space-x-1.5 transition shadow-sm"
                  title="Open video file from your computer (stays local)"
                  data-testid="open-local-video-btn"
                >
                  <FileVideo className="w-3.5 h-3.5" />
                  <span>Open Local Video</span>
                </button>

              </div>
            </div>

            {/* Source Pills */}
            <div className="flex space-x-2 overflow-x-auto pb-1">
              {/* Local Video Pill */}
              {localVideo && (
                <button
                  onClick={handleSelectLocalVideo}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 flex items-center space-x-1.5 transition border ${
                    activeSourceType === 'local'
                      ? 'bg-emerald-600 text-white border-emerald-500 shadow'
                      : 'bg-slate-800 text-slate-300 border-emerald-500/30 hover:bg-slate-750 hover:text-white'
                  }`}
                  title={`Local file: ${localVideo.filename} (${formatFileSize(localVideo.sizeBytes)})`}
                >
                  <HardDrive className="w-3.5 h-3.5 text-emerald-300" />
                  <span className="truncate max-w-[130px]">{localVideo.filename}</span>
                  <span className="text-[10px] bg-emerald-950 text-emerald-300 px-1.5 py-0.2 rounded font-mono">
                    Local
                  </span>
                </button>
              )}

              {/* Server Video Pills */}
              {videos.length === 0 && !localVideo ? (
                <span className="text-xs text-slate-500 italic py-1">
                  No videos loaded. Click &quot;Open Local Video&quot; to preview a file.
                </span>
              ) : (
                videos.map((v) => {
                  const isSelected =
                    activeSourceType === 'server' && selectedVideo?.video_id === v.video_id;
                  return (
                    <button
                      key={v.video_id}
                      onClick={() => handleSelectServerVideo(v)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 flex items-center space-x-1.5 transition ${
                        isSelected
                          ? 'bg-indigo-600 text-white shadow'
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white'
                      }`}
                    >
                      <Film className="w-3.5 h-3.5" />
                      <span className="truncate max-w-[130px]">{v.filename}</span>
                    </button>
                  );
                })
              )}
            </div>

            {/* Error banner if local file could not be opened */}
            {localVideoError && (
              <div className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/40 p-2.5 rounded-lg flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{localVideoError}</span>
              </div>
            )}
          </div>

          {/* Video Player */}
          <VideoPlayer
            localVideo={activeSourceType === 'local' ? localVideo : null}
            video={activeSourceType === 'server' ? selectedVideo : null}
            activeInterval={activeInterval}
            onTimeUpdate={setCurrentTime}
            onDurationChange={setLocalVideoDuration}
            seekTime={seekTime}
            seekRequest={seekRequest}
            onOpenLocalVideo={openFileDialog}
            onReplaceVideo={activeSourceType === 'local' ? openFileDialog : undefined}
            onClearVideo={activeSourceType === 'local' ? handleClearLocal : undefined}
          />

          {/* Interactive Clip Selection Panel for Local Videos */}
          {activeSourceType === 'local' && localVideo && (
            <ClipSelectionPanel
              localVideo={localVideo}
              currentTime={currentTime}
              videoDuration={localVideoDuration || localVideo.durationSeconds || 0}
              selections={localSelections}
              activeInterval={activeInterval}
              onAddSelection={handleAddSelection}
              onUpdateSelection={handleUpdateSelection}
              onRemoveSelection={handleRemoveSelection}
              onPreviewInterval={handlePreviewInterval}
              onJumpTo={handleJumpTo}
              onClearActiveInterval={() => setActiveInterval(null)}
              onOpenExtraction={handleOpenExtraction}
            />
          )}

          {/* Staged Extracted Clip Card */}
          {activeSourceType === 'local' && stagedClip && (
            <StagedClipCard
              stagedClip={stagedClip}
              onReplace={() => {
                setExtractionTargetInterval({
                  start: stagedClip.sourceStartSeconds,
                  end: stagedClip.sourceEndSeconds,
                  label: stagedClip.notes,
                });
                setIsExtractionOpen(true);
              }}
              onClear={handleClearStagedClip}
              onAnalyze={() => handleAnalyzeStagedClip(stagedClip)}
              isAnalyzing={isClipAnalyzing}
              analysisProgressText={clipAnalysisProgressText}
              uploadProgress={clipUploadProgress}
              analysisError={clipAnalysisError}
              onRetryAnalysis={() => handleAnalyzeStagedClip(stagedClip)}
            />
          )}

          {/* Video Actions Banner */}
          {activeSourceType === 'local' && localVideo && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <HardDrive className="w-3 h-3" />
                    <span>Local video — Not uploaded</span>
                  </span>
                  <span className="text-white text-xs font-medium truncate max-w-[170px]" title={localVideo.filename}>
                    {localVideo.filename}
                  </span>
                  <span className="text-slate-500 text-xs font-mono">
                    • {formatFileSize(localVideo.sizeBytes)}
                  </span>
                </div>

                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={openFileDialog}
                    className="px-2.5 py-1 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition flex items-center space-x-1"
                    title="Choose a different video file from your computer"
                  >
                    <FileVideo className="w-3 h-3 text-indigo-400" />
                    <span>Replace</span>
                  </button>

                  <button
                    onClick={handleClearLocal}
                    className="p-1 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
                    title="Clear selected local video"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="text-[11px] text-slate-400 bg-slate-950/60 border border-slate-800/80 rounded-lg p-2.5 flex items-center justify-between">
                <span>
                  Original video stays on your computer. Select an interval up to 10 minutes; CASTLE extracts and analyzes that clip.
                </span>
                <span className="text-emerald-400 font-mono text-[10px] shrink-0 ml-2 font-semibold">
                  Local-First
                </span>
              </div>
            </div>
          )}

          {activeSourceType === 'server' && selectedVideo && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex items-center justify-between">
              <div className="text-xs text-slate-400">
                <span className="text-white font-medium">{selectedVideo.filename}</span>
                <span className="mx-1.5">•</span>
                <span>{selectedVideo.duration_seconds?.toFixed(1)}s</span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleRunVideoUnderstanding}
                  disabled={isAnalyzing}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition shadow flex items-center space-x-1.5"
                >
                  {isAnalyzing ? (
                    <>
                      <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                      <span>Qwen Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3 h-3" />
                      <span>{analysis ? 'Re-run Analysis' : 'Run Qwen Understanding'}</span>
                    </>
                  )}
                </button>

              </div>
            </div>
          )}
        </div>

        {/* Video understanding and question generation */}
        <div className="lg:col-span-5 flex flex-col space-y-4">
          {/* Main Workspace Navigation */}
          <div data-testid="results-tab-navigation" className="bg-slate-900 border border-slate-800 rounded-xl p-1.5 flex items-center justify-between">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('understanding')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
                  activeTab === 'understanding'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Video Understanding</span>
              </button>

              <button
                onClick={() => setActiveTab('questions')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
                  activeTab === 'questions'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Generate Questions</span>
              </button>
            </div>
          </div>

          {/* Active View Container */}
          <div className="flex-1">
            <div className={activeTab === 'understanding' ? '' : 'hidden'}>
              <TimelineView
                analysis={analysis}
                currentTime={currentTime}
                onSelectInterval={handleSeekInterval}
                onRunAnalysis={
                  activeSourceType === 'server'
                    ? handleRunVideoUnderstanding
                    : stagedClip
                    ? () => handleAnalyzeStagedClip(stagedClip)
                    : undefined
                }
                isAnalyzing={activeSourceType === 'server' ? isAnalyzing : isClipAnalyzing}
                onAnalysisUpdated={(updated) => setAnalysis(updated)}
              />
            </div>
            <div className={activeTab === 'questions' ? '' : 'hidden'}>
              <QuestionGenerationWorkspace
                analysis={analysis}
                isGenerating={isGeneratingQuestions}
                onGenerate={handleGenerateQuestions}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      {localVideo && isExtractionOpen && (
        <ClipExtractionModal
          isOpen={isExtractionOpen}
          onClose={() => setIsExtractionOpen(false)}
          localVideo={localVideo}
          interval={
            extractionTargetInterval || {
              start: 0,
              end: Math.min(10, localVideoDuration || 10),
            }
          }
          onClipStaged={handleClipStaged}
        />
      )}
    </div>
  );
};
