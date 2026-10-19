import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, RotateCcw, Volume2, VolumeX, Maximize } from 'lucide-react';
import { api } from '../../shared/api/client';
import { VideoItem } from '../../shared/types';

interface VideoPlayerProps {
  video: VideoItem | null;
  activeInterval?: { start: number; end: number } | null;
  onTimeUpdate?: (currentTime: number) => void;
  seekTime?: number | null;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  video,
  activeInterval,
  onTimeUpdate,
  seekTime,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    if (seekTime !== undefined && seekTime !== null && videoRef.current) {
      videoRef.current.currentTime = seekTime;
      if (!isPlaying) {
        videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      }
    }
  }, [seekTime]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const cur = videoRef.current.currentTime;
      setCurrentTime(cur);
      if (onTimeUpdate) onTimeUpdate(cur);

      // Loop or stop if active interval bounds exist and exceeded
      if (activeInterval && cur >= activeInterval.end) {
        videoRef.current.pause();
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
      if (activeInterval && (currentTime < activeInterval.start || currentTime >= activeInterval.end)) {
        videoRef.current.currentTime = activeInterval.start;
      }
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    if (videoRef.current) {
      videoRef.current.currentTime = val;
      setCurrentTime(val);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  if (!video) {
    return (
      <div className="aspect-video bg-slate-950 rounded-xl border border-slate-800 flex flex-col items-center justify-center text-slate-500">
        <p className="text-sm">No video selected</p>
        <p className="text-xs text-slate-600 mt-1">Select or upload a video to begin analysis</p>
      </div>
    );
  }

  const streamUrl = api.getVideoStreamUrl(video.video_id);

  return (
    <div className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden shadow-lg flex flex-col">
      <div className="relative aspect-video bg-black flex items-center justify-center">
        <video
          ref={videoRef}
          src={streamUrl}
          className="w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => {
            if (videoRef.current) setDuration(videoRef.current.duration || video.duration_seconds);
          }}
          onEnded={() => setIsPlaying(false)}
        />

        {activeInterval && (
          <div className="absolute top-3 left-3 bg-indigo-900/80 backdrop-blur border border-indigo-500/50 text-indigo-200 text-xs px-2.5 py-1 rounded-md font-mono flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
            <span>Evidence: {formatTime(activeInterval.start)} - {formatTime(activeInterval.end)}</span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="p-3 bg-slate-900/95 border-t border-slate-800 space-y-2">
        <div className="relative flex items-center">
          <input
            type="range"
            min={0}
            max={duration || video.duration_seconds || 100}
            step={0.1}
            value={currentTime}
            onChange={handleScrub}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
        </div>

        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-3">
            <button
              onClick={togglePlay}
              className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition"
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
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
              title="Reset"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            <span className="font-mono text-slate-300">
              {formatTime(currentTime)} / {formatTime(duration || video.duration_seconds)}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                if (videoRef.current) {
                  videoRef.current.muted = !isMuted;
                  setIsMuted(!isMuted);
                }
              }}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
            >
              {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>

            <span className="text-[11px] text-slate-500 font-mono">
              {video.width}x{video.height} • {video.fps?.toFixed(0)}fps
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

