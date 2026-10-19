import React, { useState, useEffect } from 'react';
import {
  Video as VideoIcon,
  Sparkles,
  HelpCircle,
  FileCheck2,
  Play,
  Film,
  Plus,
  ArrowRight,
} from 'lucide-react';
import { api } from './services/api';
import {
  AnnotationReviewSession,
  InferenceJob,
  VideoAnalysis,
  VideoItem,
} from './types';
import { Header } from './components/Header';
import { VideoPlayer } from './components/VideoPlayer';
import { TimelineView } from './components/TimelineView';
import { GroundedQAPanel } from './components/GroundedQAPanel';
import { AnnotationReviewWorkspace } from './components/AnnotationReviewWorkspace';
import { VideoUploadModal } from './components/VideoUploadModal';
import { WhodunnitExportModal } from './components/WhodunnitExportModal';

export const App: React.FC = () => {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoItem | null>(null);
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [reviewSession, setReviewSession] = useState<AnnotationReviewSession | null>(null);

  const [currentTime, setCurrentTime] = useState(0);
  const [seekTime, setSeekTime] = useState<number | null>(null);
  const [activeInterval, setActiveInterval] = useState<{ start: number; end: number } | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingQuestions, setIsGeneratingQuestions] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'qa' | 'review'>('timeline');

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Load videos on mount
  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    try {
      const res = await api.getVideos();
      setVideos(res.videos);
      if (res.videos.length > 0 && !selectedVideo) {
        handleSelectVideo(res.videos[0]);
      }
    } catch (err) {
      console.error('Failed to load videos', err);
    }
  };

  const handleSelectVideo = async (video: VideoItem) => {
    setSelectedVideo(video);
    setAnalysis(null);
    setReviewSession(null);
    setActiveInterval(null);

    // Try loading analysis for this video
    try {
      const an = await api.getAnalysis(video.video_id);
      setAnalysis(an);
      // Also try to load or create review session
      const rev = await api.createOrLoadReviewSession(video.video_id, video.video_id);
      setReviewSession(rev);
    } catch {
      // Analysis doesn't exist yet for this video
    }
  };

  const handleRunVideoUnderstanding = async () => {
    if (!selectedVideo) return;
    setIsAnalyzing(true);

    try {
      const { job_id } = await api.submitVideoUnderstanding(selectedVideo.video_id);
      const finishedJob = await api.pollJobUntilFinished(job_id);

      if (finishedJob.status === 'completed' && finishedJob.result_id) {
        const loadedAnalysis = await api.getAnalysis(finishedJob.result_id);
        setAnalysis(loadedAnalysis);

        const rev = await api.createOrLoadReviewSession(
          finishedJob.result_id,
          selectedVideo.video_id
        );
        setReviewSession(rev);
      }
    } catch (err) {
      console.error('Video understanding failed', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateQuestions = async () => {
    if (!analysis || !selectedVideo) return;
    setIsGeneratingQuestions(true);

    try {
      const { job_id } = await api.submitQuestionGeneration(
        analysis.analysis_id,
        selectedVideo.duration_seconds || 30.0,
        5
      );
      const finishedJob = await api.pollJobUntilFinished(job_id);

      if (finishedJob.status === 'completed' && finishedJob.result_id) {
        // Refresh review session with the generated questions
        const rev = await api.createOrLoadReviewSession(
          analysis.analysis_id,
          selectedVideo.video_id,
          finishedJob.result_id
        );
        setReviewSession(rev);
        setActiveTab('review');
      }
    } catch (err) {
      console.error('Question generation failed', err);
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
      <Header onOpenUpload={() => setIsUploadOpen(true)} videoCount={videos.length} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Video Selector & Player (5 cols) */}
        <div className="lg:col-span-5 flex flex-col space-y-4">
          {/* Video Selector Pill Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Video Library
              </span>
              <button
                onClick={() => setIsUploadOpen(true)}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
              >
                <Plus className="w-3 h-3" />
                <span>Add Video</span>
              </button>
            </div>

            <div className="flex space-x-2 overflow-x-auto pb-1">
              {videos.length === 0 ? (
                <span className="text-xs text-slate-500 italic">No videos uploaded yet.</span>
              ) : (
                videos.map((v) => {
                  const isSelected = selectedVideo?.video_id === v.video_id;
                  return (
                    <button
                      key={v.video_id}
                      onClick={() => handleSelectVideo(v)}
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
          </div>

          {/* Video Player */}
          <VideoPlayer
            video={selectedVideo}
            activeInterval={activeInterval}
            onTimeUpdate={setCurrentTime}
            seekTime={seekTime}
          />

          {/* Video Actions Banner */}
          {selectedVideo && (
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

                {analysis && (
                  <button
                    onClick={handleGenerateQuestions}
                    disabled={isGeneratingQuestions}
                    className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-300 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-700 transition flex items-center space-x-1.5"
                  >
                    {isGeneratingQuestions ? (
                      <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    ) : (
                      <HelpCircle className="w-3 h-3 text-indigo-400" />
                    )}
                    <span>Generate Questions</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Multi-tab Workspace (7 cols) */}
        <div className="lg:col-span-7 flex flex-col space-y-4">
          {/* Main Workspace Navigation */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-1.5 flex items-center justify-between">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('timeline')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
                  activeTab === 'timeline'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Observable Events</span>
              </button>

              <button
                onClick={() => setActiveTab('qa')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
                  activeTab === 'qa'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Grounded Video QA</span>
              </button>

              <button
                onClick={() => setActiveTab('review')}
                className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
                  activeTab === 'review'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <FileCheck2 className="w-3.5 h-3.5" />
                <span>Whodunnit Review</span>
                {reviewSession && (
                  <span className="ml-1 bg-indigo-900 text-indigo-300 text-[10px] px-1.5 py-0.2 rounded-full">
                    {reviewSession.events.length + reviewSession.questions.length}
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Active View Container */}
          <div className="flex-1">
            {activeTab === 'timeline' && (
              <TimelineView
                analysis={analysis}
                currentTime={currentTime}
                onSelectInterval={handleSeekInterval}
                onRunAnalysis={handleRunVideoUnderstanding}
                isAnalyzing={isAnalyzing}
              />
            )}

            {activeTab === 'qa' && (
              <GroundedQAPanel
                videoId={selectedVideo?.video_id || null}
                analysisId={analysis?.analysis_id || null}
                onSeekInterval={handleSeekInterval}
              />
            )}

            {activeTab === 'review' && (
              <AnnotationReviewWorkspace
                session={reviewSession}
                onSessionUpdated={setReviewSession}
                onOpenExportModal={() => setIsExportOpen(true)}
                onSeekInterval={handleSeekInterval}
              />
            )}
          </div>
        </div>
      </main>

      {/* Modals */}
      <VideoUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploaded={(v) => {
          setVideos((prev) => [v, ...prev]);
          handleSelectVideo(v);
        }}
      />

      <WhodunnitExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        reviewId={reviewSession?.review_id || null}
      />
    </div>
  );
};

