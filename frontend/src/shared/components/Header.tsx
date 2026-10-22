import React from 'react';
import { Video, ShieldCheck } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="bg-indigo-600/20 text-indigo-400 p-2 rounded-lg border border-indigo-500/30">
          <Video className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-white tracking-tight">CASTLE QA Studio</h1>
            <span className="text-xs bg-emerald-500/10 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30">
              Local-first
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Open a local recording, select an interval, prepare clips, review and export.
          </p>
        </div>
      </div>

      <div className="flex items-center">
        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>Your original video stays on this device</span>
        </div>
      </div>
    </header>
  );
};
