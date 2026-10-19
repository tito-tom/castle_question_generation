import React, { useState, useEffect } from 'react';
import { X, Download, FileSpreadsheet, Copy, Check, Info } from 'lucide-react';
import { api } from '../../shared/api/client';

interface WhodunnitExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  reviewId: string | null;
}

export const WhodunnitExportModal: React.FC<WhodunnitExportModalProps> = ({
  isOpen,
  onClose,
  reviewId,
}) => {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen && reviewId) {
      setLoading(true);
      fetch(api.getWhodunnitExportUrl(reviewId))
        .then((r) => r.json())
        .then((json) => setData(json))
        .catch((err) => console.error('Failed to load export JSON', err))
        .finally(() => setLoading(false));
    }
  }, [isOpen, reviewId]);

  if (!isOpen || !reviewId) return null;

  const handleCopy = () => {
    if (data) {
      navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadJson = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `whodunnit_export_${reviewId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
              <Download className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Whodunnit Annotation Export</h3>
              <p className="text-[11px] text-slate-400">
                Verified human annotations formatted for Whodunnit criteria
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Notice alert */}
        <div className="mx-4 mt-3 bg-indigo-950/40 border border-indigo-800/40 rounded-lg p-2.5 flex items-start space-x-2 text-xs text-indigo-200">
          <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-relaxed">
            <strong>Configurable Adapter:</strong> Generated according to Whodunnit draft criteria. Distractor actors, grounded timestamps, and verified actions are bundled ready for final Whodunnit deployment.
          </div>
        </div>

        {/* JSON Preview */}
        <div className="p-4 flex-1 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 font-mono">Payload Preview (JSON)</span>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleCopy}
                className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white bg-slate-800 px-2.5 py-1 rounded transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800 p-3 overflow-auto font-mono text-[11px] text-slate-300">
            {loading ? (
              <div className="flex items-center justify-center h-full text-slate-500">
                Generating export package...
              </div>
            ) : data ? (
              <pre>{JSON.stringify(data, null, 2)}</pre>
            ) : (
              <div className="text-slate-500">No data available</div>
            )}
          </div>
        </div>

        {/* Actions Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <a
            href={api.getWhodunnitCsvExportUrl(reviewId)}
            download
            className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded-lg transition border border-slate-700"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>Download CSV Spreadsheets</span>
          </a>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="text-xs text-slate-400 hover:text-white px-3 py-2 rounded-lg"
            >
              Close
            </button>
            <button
              onClick={handleDownloadJson}
              className="flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition shadow"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download JSON Package</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

