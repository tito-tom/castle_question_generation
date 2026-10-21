import React from 'react';
import { Video, ShieldCheck, Cpu, UploadCloud, FileVideo } from 'lucide-react';

interface HeaderProps {
  onOpenLocalVideo?: () => void;
  onOpenUpload: () => void;
  videoCount: number;
  hasLocalVideo?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenLocalVideo,
  onOpenUpload,
  videoCount,
  hasLocalVideo = false,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="bg-indigo-600/20 text-indigo-400 p-2 rounded-lg border border-indigo-500/30">
          <Video className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-white tracking-tight">CASTLE QA Studio</h1>
            <span className="text-xs bg-indigo-500/20 text-indigo-300 font-mono px-2 py-0.5 rounded border border-indigo-500/30">
              Qwen2.5-VL
            </span>
          </div>
          <p className="text-xs text-slate-400">
            AI Video Understanding & Grounded Whodunnit Annotation Platform
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-md border border-slate-700/50">
          <Cpu className="w-3.5 h-3.5 text-emerald-400" />
          <span>GPU Queue Ready</span>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        </div>

        <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-md border border-slate-700/50">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>{videoCount} Server Video{videoCount === 1 ? '' : 's'}</span>
          {hasLocalVideo && (
            <span className="ml-1 px-1.5 py-0.2 bg-emerald-500/20 text-emerald-300 rounded text-[10px]">
              + 1 Local
            </span>
          )}
        </div>

        {onOpenLocalVideo && (
          <button
            onClick={onOpenLocalVideo}
            className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg shadow-sm transition"
            title="Open a video from your computer for instant preview without uploading"
          >
            <FileVideo className="w-4 h-4" />
            <span>Open Local Video</span>
          </button>
        )}

        <button
          onClick={onOpenUpload}
          className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium px-3.5 py-2 rounded-lg border border-slate-700 transition"
          title="Upload video to server"
        >
          <UploadCloud className="w-4 h-4 text-slate-400" />
          <span>Upload to Server</span>
        </button>
      </div>
    </header>
  );
};
