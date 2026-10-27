import React, { useState } from 'react';
import { X, UploadCloud, FileVideo, AlertCircle } from 'lucide-react';
import { api } from '../../shared/api/client';
import { VideoItem } from '../../shared/types';

interface VideoUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: (video: VideoItem) => void;
}

export const VideoUploadModal: React.FC<VideoUploadModalProps> = ({
  isOpen,
  onClose,
  onUploaded,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);

    try {
      const item = await api.uploadVideo(file);
      onUploaded(item);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full shadow-2xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <UploadCloud className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-white">Upload Short Video</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Dropzone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          className="border-2 border-dashed border-slate-800 hover:border-indigo-500/60 rounded-xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center bg-slate-950/40"
          onClick={() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'video/mp4,video/quicktime,video/webm';
            input.onchange = (e) => {
              const target = e.target as HTMLInputElement;
              if (target.files && target.files[0]) {
                setFile(target.files[0]);
                setError(null);
              }
            };
            input.click();
          }}
        >
          <FileVideo className="w-8 h-8 text-indigo-400 mb-2" />
          <p className="text-xs text-slate-300 font-medium">
            {file ? file.name : 'Click to select or drag video file here'}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">
            Supports MP4, MOV, WebM (Short clips recommended)
          </p>
          {file && (
            <span className="text-[10px] text-slate-400 mt-2 font-mono bg-slate-800 px-2 py-0.5 rounded">
              {(file.size / (1024 * 1024)).toFixed(2)} MB
            </span>
          )}
        </div>

        {error && (
          <div className="text-xs text-rose-400 bg-rose-950/40 border border-rose-800/40 p-2.5 rounded-lg flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            disabled={isUploading}
            className="text-xs text-slate-400 hover:text-white px-3 py-1.5"
          >
            Cancel
          </button>

          <button
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg transition shadow flex items-center space-x-1.5"
          >
            {isUploading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                <span>Uploading...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Upload & Ingest</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

