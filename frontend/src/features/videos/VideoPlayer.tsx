import React, { useRef, useState, useEffect } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  HardDrive,
  Cloud,
  X,
  FileVideo,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { api } from '../../shared/api/client';
import { VideoItem, LocalVideoItem, formatFileSize } from '../../shared/types';
import { formatTimestamp, formatDuration } from './timestampUtils';

export interface VideoSeekRequest {
  time: number;
  autoPlay?: boolean;
  id: number;
}

export interface VideoPlayerProps {
  video?: VideoItem | null;
  localVideo?: LocalVideoItem | null;
  activeInterval?: { start: number; end: number } | null;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
  seekTime?: number | null;
  seekRequest?: VideoSeekRequest | null;
  onReplaceVideo?: () => void;
  onClearVideo?: () => void;
  onOpenLocalVideo?: () => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  video,
  localVideo,
  activeInterval,
  onTimeUpdate,
  onDurationChange,
  seekTime,
  seekRequest,
  onReplaceVideo,
  onClearVideo,
  onOpenLocalVideo,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Determine active video source
  const isLocal = Boolean(localVideo);
  const activeVideo = localVideo || video;

  // Stream URL or Local Object URL
  const videoSrc = localVideo
    ? localVideo.objectUrl
    : video
    ? api.getVideoStreamUrl(video.video_id)
    : undefined;

  // Reset state whenever the active video changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setLoadError(null);
    setIsLoading(Boolean(videoSrc));
  }, [videoSrc]);

  // Handle seek requests with autoPlay control
  useEffect(() => {
    if (seekRequest && videoRef.current) {
      videoRef.current.currentTime = seekRequest.time;
      setCurrentTime(seekRequest.time);
      if (seekRequest.autoPlay) {
        videoRef.current
          .play()
          .then(() => setIsPlaying(true))
          .catch(() => {});
      } else {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    }
  }, [seekRequest]);

  // Backward compatibility for existing seekTime prop
  useEffect(() => {
    if (seekTime !== undefined && seekTime !== null && videoRef.current) {
      videoRef.current.currentTime = seekTime;
      setCurrentTime(seekTime);
      if (!isPlaying) {
        videoRef.current
          .play()
          .then(() => setIsPlaying(true))
          .catch(() => {});
      }
    }
  }, [seekTime]);

  // Periodic session activity renewal while playing a temporary server clip
  useEffect(() => {
    if (!isPlaying || !video?.is_temporary || !video?.session_id) return;

    const interval = setInterval(() => {
      api.touchSession(video.session_id!, video.session_token).catch(() => {});
    }, 60000); // Renew every 60s during active playback

    return () => clearInterval(interval);
  }, [isPlaying, video?.is_temporary, video?.session_id, video?.session_token]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const cur = videoRef.current.currentTime;
      setCurrentTime(cur);
      if (onTimeUpdate) onTimeUpdate(cur);

      // Loop or stop if active interval bounds exist and exceeded
      if (activeInterval && cur >= activeInterval.end) {
        videoRef.current.pause();
        videoRef.current.currentTime = activeInterval.end;
        setCurrentTime(activeInterval.end);
        setIsPlaying(false);
      }
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      if (
        activeInterval &&
        (currentTime < activeInterval.start || currentTime >= activeInterval.end)
      ) {
        videoRef.current.currentTime = activeInterval.start;
      }
      videoRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => {
          console.warn('Playback error:', err);
          setIsPlaying(false);
        });
    }
  };

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    if (videoRef.current) {
      videoRef.current.currentTime = val;
      setCurrentTime(val);
    }
  };

  const handleVideoError = () => {
    setIsLoading(false);
    setIsPlaying(false);
    const mediaError = videoRef.current?.error;
    let message = 'Failed to load video.';
    if (mediaError) {
      switch (mediaError.code) {
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          message =
            'The video format or codec is not supported by your browser. Recommended: MP4 (H.264/AAC) or WebM.';
          break;
        case MediaError.MEDIA_ERR_DECODE:
          message =
            'An error occurred while decoding the video stream. The file may be corrupt or encoded with an unsupported profile.';
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          message = 'A network error caused the video download to fail.';
          break;
        case MediaError.MEDIA_ERR_ABORTED:
          message = 'Video playback was aborted.';
          break;
        default:
          message = `Video playback error (${mediaError.message || 'unknown error'})`;
      }
    }
    setLoadError(message);
  };

  const formatTime = (secs: number) => {
    if (isNaN(secs) || secs < 0) return '00:00.0';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  // If no video is selected, show rich empty state
  if (!activeVideo || !videoSrc) {
    return (
      <div className="aspect-video bg-slate-950 rounded-xl border border-slate-800 flex flex-col items-center justify-center text-slate-500 p-6 text-center shadow-lg">
        <div className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mb-3 text-slate-400">
          <FileVideo className="w-6 h-6 text-indigo-400" />
        </div>
        <p className="text-sm font-semibold text-slate-200">No video selected</p>
        <p className="text-xs text-slate-500 mt-1 max-w-sm">
          Open a local video from your device for instant private preview without uploading, or choose a video from your library.
        </p>
        {onOpenLocalVideo && (
          <button
            onClick={onOpenLocalVideo}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow transition flex items-center space-x-2"
          >
            <FileVideo className="w-4 h-4" />
            <span>Open Local Video</span>
          </button>
        )}
      </div>
    );
  }

  const filename = localVideo ? localVideo.filename : (video?.filename || '');
  const sizeBytes = localVideo ? localVideo.sizeBytes : (video?.size_bytes || 0);
  const expectedDuration = localVideo ? localVideo.durationSeconds : video?.duration_seconds;

  return (
    <div className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden shadow-lg flex flex-col">
      {/* Top Info Bar */}
      <div className="px-3.5 py-2 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2 truncate mr-2">
          {isLocal ? (
            <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shrink-0">
              <HardDrive className="w-3 h-3" />
              <span>Local video — Not uploaded</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 shrink-0">
              <Cloud className="w-3 h-3" />
              <span>Server Video</span>
            </span>
          )}
          <span className="text-slate-300 font-medium truncate max-w-[200px]" title={filename}>
            {filename}
          </span>
          <span className="text-slate-500 font-mono text-[11px] shrink-0">
            ({formatFileSize(sizeBytes)})
          </span>
        </div>

        <div className="flex items-center space-x-1 shrink-0">
          {onReplaceVideo && (
            <button
              onClick={onReplaceVideo}
              className="px-2 py-1 rounded text-[11px] font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition flex items-center space-x-1"
              title="Replace current video"
            >
              <FileVideo className="w-3 h-3 text-indigo-400" />
              <span>Replace</span>
            </button>
          )}

          {onClearVideo && (
            <button
              onClick={onClearVideo}
              className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
              title="Clear selected video"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Video Screen Area */}
      <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
        <video
          ref={videoRef}
          src={videoSrc}
          preload="metadata"
          data-testid="video-element"
          className="w-full h-full object-contain"
          onLoadStart={() => {
            setIsLoading(true);
            setLoadError(null);
          }}
          onCanPlay={() => setIsLoading(false)}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => {
            setIsLoading(false);
            if (videoRef.current) {
              const dur = videoRef.current.duration || expectedDuration || 0;
              setDuration(dur);
              if (onDurationChange) {
                onDurationChange(dur);
              }
            }
          }}
          onError={handleVideoError}
          onEnded={() => setIsPlaying(false)}
        />

        {/* Loading Spinner */}
        {isLoading && !loadError && (
          <div className="absolute inset-0 bg-black/50 backdrop-blur-xs flex flex-col items-center justify-center text-slate-300 space-y-2 pointer-events-none">
            <Loader2 className="w-7 h-7 text-indigo-400 animate-spin" />
            <span className="text-xs">Loading media metadata...</span>
          </div>
        )}

        {/* Error Overlay */}
        {loadError && (
          <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm p-6 flex flex-col items-center justify-center text-center space-y-3 z-10">
            <div className="w-10 h-10 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="max-w-md space-y-1">
              <p className="text-xs font-semibold text-rose-300">Video Playback Error</p>
              <p className="text-xs text-slate-400 leading-relaxed">{loadError}</p>
            </div>
            {onReplaceVideo && (
              <button
                onClick={onReplaceVideo}
                className="mt-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 rounded-lg border border-slate-700 transition flex items-center space-x-1.5"
              >
                <FileVideo className="w-3.5 h-3.5 text-indigo-400" />
                <span>Select Another Video</span>
              </button>
            )}
          </div>
        )}

        {/* Active Interval Overlay */}
        {activeInterval && !loadError && (
          <div
            data-testid="active-interval-overlay"
            className="absolute top-3 left-3 bg-indigo-900/80 backdrop-blur border border-indigo-500/50 text-indigo-200 text-xs px-2.5 py-1 rounded-md font-mono flex items-center space-x-1.5 shadow"
          >
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
            <span>
              {isLocal ? 'Selection Preview: ' : 'Evidence: '}
              {isLocal
                ? `${formatTimestamp(activeInterval.start)} – ${formatTimestamp(activeInterval.end)} (${formatDuration(activeInterval.end - activeInterval.start)})`
                : `${formatTime(activeInterval.start)} - ${formatTime(activeInterval.end)}`}
            </span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="p-3 bg-slate-900/95 border-t border-slate-800 space-y-2">
        <div className="relative flex items-center">
          <input
            type="range"
            min={0}
            max={duration || expectedDuration || 100}
            step={0.1}
            value={currentTime}
            onChange={handleScrub}
            disabled={Boolean(loadError)}
            aria-label="Video playback timeline"
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500 disabled:opacity-40"
          />
        </div>

        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-3">
            <button
              onClick={togglePlay}
              disabled={Boolean(loadError)}
              className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white transition shadow"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>

            <button
              onClick={() => {
                if (videoRef.current) {
                  videoRef.current.currentTime = 0;
                  setCurrentTime(0);
                }
              }}
              disabled={Boolean(loadError)}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white disabled:opacity-40 transition"
              title="Reset to 00:00"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            <span className="font-mono text-slate-300" data-testid="video-time-display">
              {isLocal ? formatTimestamp(currentTime) : formatTime(currentTime)} / {isLocal ? formatTimestamp(duration || expectedDuration || 0) : formatTime(duration || expectedDuration || 0)}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                if (videoRef.current) {
                  videoRef.current.muted = !isMuted;
                  setIsMuted(!isMuted);
                }
              }}
              disabled={Boolean(loadError)}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white disabled:opacity-40 transition"
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>

            {video && video.width && video.height && (
              <span className="text-[11px] text-slate-500 font-mono">
                {video.width}x{video.height}
                {video.fps ? ` • ${video.fps.toFixed(0)}fps` : ''}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
