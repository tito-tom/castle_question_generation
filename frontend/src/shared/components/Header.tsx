import React from 'react';
import { Video, ShieldCheck, Cpu, UploadCloud } from 'lucide-react';

interface HeaderProps {
  onOpenUpload: () => void;
  videoCount: number;
}

export const Header: React.FC<HeaderProps> = ({ onOpenUpload, videoCount }) => {
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

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-md border border-slate-700/50">
          <Cpu className="w-3.5 h-3.5 text-emerald-400" />
          <span>GPU Queue Ready</span>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-md border border-slate-700/50">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>{videoCount} Videos Loaded</span>
        </div>

        <button
          onClick={onOpenUpload}
          className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg shadow-sm transition"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Upload Video</span>
        </button>
      </div>
    </header>
  );
};

