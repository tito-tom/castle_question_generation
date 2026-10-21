import { useState, useRef, useEffect, useCallback } from 'react';
import { LocalVideoItem } from '../../shared/types';

export interface UseLocalVideoResult {
  localVideo: LocalVideoItem | null;
  error: string | null;
  selectFile: (file: File) => boolean;
  clearLocalVideo: () => void;
  openFileDialog: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
}

const SUPPORTED_VIDEO_MIME_PREFIX = 'video/';
const COMMON_VIDEO_EXTENSIONS = [
  '.mp4',
  '.webm',
  '.mov',
  '.ogg',
  '.ogv',
  '.mkv',
  '.m4v',
  '.avi',
];

export function isSupportedVideoFile(file: File): boolean {
  if (file.type && file.type.startsWith(SUPPORTED_VIDEO_MIME_PREFIX)) {
    return true;
  }
  const lowerName = file.name.toLowerCase();
  return COMMON_VIDEO_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

/**
 * Generate a collision-resistant client-side identifier for an opened local video instance.
 */
export function generateSourceInstanceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `src_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

export function useLocalVideo(onVideoSelected?: (video: LocalVideoItem) => void): UseLocalVideoResult {
  const [localVideo, setLocalVideo] = useState<LocalVideoItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Keep track of the active object URL so it can be revoked when replaced or on unmount
  const objectUrlRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const cleanupObjectUrl = useCallback(() => {
    if (objectUrlRef.current) {
      try {
        URL.revokeObjectURL(objectUrlRef.current);
      } catch {
        // Safe fallback in non-browser/test environments
      }
      objectUrlRef.current = null;
    }
  }, []);

  // Cleanup object URL on unmount
  useEffect(() => {
    return () => {
      cleanupObjectUrl();
    };
  }, [cleanupObjectUrl]);

  const clearLocalVideo = useCallback(() => {
    cleanupObjectUrl();
    setLocalVideo(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [cleanupObjectUrl]);

  const selectFile = useCallback(
    (file: File): boolean => {
      // 1. Validate file existence and size
      if (!file) {
        setError('No file was selected.');
        return false;
      }

      if (file.size === 0) {
        setError(`Cannot load "${file.name}" because the file is empty (0 bytes).`);
        return false;
      }

      // 2. Validate MIME type or file extension
      if (!isSupportedVideoFile(file)) {
        setError(
          `"${file.name}" does not appear to be a supported video file. Please select an MP4, WebM, MOV, or other browser-compatible video format.`
        );
        return false;
      }

      // 3. Revoke any previous object URL before allocating a new one
      cleanupObjectUrl();

      // 4. Create a fresh temporary object URL (does NOT upload or read entire file into RAM)
      let objectUrl = '';
      try {
        objectUrl = URL.createObjectURL(file);
      } catch (err) {
        setError('Failed to create browser media URL for the selected file.');
        return false;
      }

      objectUrlRef.current = objectUrl;

      const item: LocalVideoItem = {
        sourceType: 'local',
        sourceInstanceId: generateSourceInstanceId(),
        file,
        objectUrl,
        filename: file.name,
        sizeBytes: file.size,
      };

      setLocalVideo(item);
      setError(null);

      if (onVideoSelected) {
        onVideoSelected(item);
      }

      return true;
    },
    [cleanupObjectUrl, onVideoSelected]
  );

  const openFileDialog = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  }, []);

  return {
    localVideo,
    error,
    selectFile,
    clearLocalVideo,
    openFileDialog,
    fileInputRef,
  };
}

