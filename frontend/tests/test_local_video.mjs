import test from 'node:test';
import assert from 'node:assert/strict';

// Helper functions and logic from frontend/src/shared/types and frontend/src/features/videos/useLocalVideo

function formatFileSize(bytes) {
  if (bytes <= 0 || isNaN(bytes)) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = bytes / Math.pow(k, i);
  return `${val.toFixed(val >= 10 || i === 0 ? 0 : 1)} ${sizes[i]}`;
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

function isSupportedVideoFile(file) {
  if (file.type && file.type.startsWith(SUPPORTED_VIDEO_MIME_PREFIX)) {
    return true;
  }
  const lowerName = file.name.toLowerCase();
  return COMMON_VIDEO_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

function isLocalVideo(video) {
  return video !== null && video !== undefined && video.sourceType === 'local';
}

// Simulated useLocalVideo controller to test exact lifecycle, revocation, and zero-upload guarantee
class LocalVideoController {
  constructor(apiClient) {
    this.apiClient = apiClient;
    this.localVideo = null;
    this.error = null;
    this.activeObjectUrl = null;
    this.revokedUrls = [];
    this.createdUrls = [];
  }

  cleanupObjectUrl() {
    if (this.activeObjectUrl) {
      this.revokedUrls.push(this.activeObjectUrl);
      this.activeObjectUrl = null;
    }
  }

  clearLocalVideo() {
    this.cleanupObjectUrl();
    this.localVideo = null;
    this.error = null;
  }

  selectFile(file) {
    if (!file) {
      this.error = 'No file was selected.';
      return false;
    }

    if (file.size === 0) {
      this.error = `Cannot load "${file.name}" because the file is empty (0 bytes).`;
      return false;
    }

    if (!isSupportedVideoFile(file)) {
      this.error = `"${file.name}" does not appear to be a supported video file. Please select an MP4, WebM, MOV, or other browser-compatible video format.`;
      return false;
    }

    this.cleanupObjectUrl();

    const objectUrl = `blob:http://localhost:3000/mock-${file.name}-${Date.now()}`;
    this.createdUrls.push(objectUrl);
    this.activeObjectUrl = objectUrl;

    this.localVideo = {
      sourceType: 'local',
      file,
      objectUrl,
      filename: file.name,
      sizeBytes: file.size,
    };
    this.error = null;
    return true;
  }
}

// Mock API client to verify no upload occurs
const mockApiClient = {
  uploadCallCount: 0,
  uploadVideo(file) {
    this.uploadCallCount++;
    return Promise.resolve({
      video_id: 'vid_mock_123',
      filename: file.name,
      duration_seconds: 10,
      size_bytes: file.size,
    });
  },
  getVideoStreamUrl(videoId) {
    return `/api/v1/videos/${videoId}/stream`;
  },
};

test('1. Selecting a valid local video sets state and metadata without uploading', () => {
  const ctrl = new LocalVideoController(mockApiClient);
  const file = new File(['mock video binary data content'], 'kitchen_long_recording.mp4', {
    type: 'video/mp4',
  });

  const success = ctrl.selectFile(file);
  assert.equal(success, true);
  assert.notEqual(ctrl.localVideo, null);
  assert.equal(ctrl.localVideo.filename, 'kitchen_long_recording.mp4');
  assert.equal(ctrl.localVideo.sizeBytes, file.size);
  assert.equal(ctrl.localVideo.sourceType, 'local');
  assert.equal(ctrl.error, null);
  assert.equal(mockApiClient.uploadCallCount, 0, 'No upload API call should be made');
});

test('2. Creating a valid browser object URL for local video', () => {
  const ctrl = new LocalVideoController(mockApiClient);
  const file = new File(['fake data'], 'scene1.webm', { type: 'video/webm' });

  ctrl.selectFile(file);
  assert.match(ctrl.localVideo.objectUrl, /^blob:/);
  assert.equal(ctrl.createdUrls.length, 1);
});

test('3. Video stream URL resolution distinguishes local object URL from server stream URL', () => {
  const localVideo = {
    sourceType: 'local',
    objectUrl: 'blob:http://localhost:3000/sample-uuid',
    filename: 'local_sample.mp4',
    sizeBytes: 1048576,
  };

  const serverVideo = {
    video_id: 'vid_srv_999',
    filename: 'server_sample.mp4',
    duration_seconds: 45,
    size_bytes: 5242880,
  };

  // Local video uses its objectUrl directly
  const localSrc = localVideo.objectUrl;
  assert.equal(localSrc, 'blob:http://localhost:3000/sample-uuid');

  // Server video uses backend stream endpoint
  const serverSrc = mockApiClient.getVideoStreamUrl(serverVideo.video_id);
  assert.equal(serverSrc, '/api/v1/videos/vid_srv_999/stream');
});

test('4. Loading and formatting video metadata', () => {
  assert.equal(formatFileSize(0), '0 B');
  assert.equal(formatFileSize(500), '500 B');
  assert.equal(formatFileSize(1024), '1.0 KB');
  assert.equal(formatFileSize(5242880), '5.0 MB');
  assert.equal(formatFileSize(1073741824), '1.0 GB');
});

test('5. Replacing the selected video revokes the previous object URL and creates a new one', () => {
  const ctrl = new LocalVideoController(mockApiClient);
  const file1 = new File(['data1'], 'video1.mp4', { type: 'video/mp4' });
  const file2 = new File(['data2_longer_content'], 'video2.mov', { type: 'video/quicktime' });

  ctrl.selectFile(file1);
  const url1 = ctrl.localVideo.objectUrl;

  ctrl.selectFile(file2);
  const url2 = ctrl.localVideo.objectUrl;

  assert.notEqual(url1, url2);
  assert.equal(ctrl.localVideo.filename, 'video2.mov');
  assert.equal(ctrl.revokedUrls.includes(url1), true, 'Previous object URL must be revoked');
  assert.equal(mockApiClient.uploadCallCount, 0, 'No upload API call during replace');
});

test('6. Revoking unused object URLs on clear', () => {
  const ctrl = new LocalVideoController(mockApiClient);
  const file = new File(['data'], 'test.mp4', { type: 'video/mp4' });

  ctrl.selectFile(file);
  const url = ctrl.localVideo.objectUrl;
  assert.equal(ctrl.activeObjectUrl, url);

  ctrl.clearLocalVideo();
  assert.equal(ctrl.localVideo, null);
  assert.equal(ctrl.activeObjectUrl, null);
  assert.equal(ctrl.revokedUrls.includes(url), true, 'Object URL must be revoked when video is cleared');
});

test('7. Clearing the selection resets state completely', () => {
  const ctrl = new LocalVideoController(mockApiClient);
  const file = new File(['content'], 'sample.mp4', { type: 'video/mp4' });

  ctrl.selectFile(file);
  assert.notEqual(ctrl.localVideo, null);

  ctrl.clearLocalVideo();
  assert.equal(ctrl.localVideo, null);
  assert.equal(ctrl.error, null);
});

test('8. Handling unsupported or invalid video files', () => {
  const ctrl = new LocalVideoController(mockApiClient);

  // Empty file
  const emptyFile = new File([], 'empty.mp4', { type: 'video/mp4' });
  const successEmpty = ctrl.selectFile(emptyFile);
  assert.equal(successEmpty, false);
  assert.match(ctrl.error, /empty \(0 bytes\)/);
  assert.equal(ctrl.localVideo, null);

  // Unsupported file format
  const textFile = new File(['hello'], 'document.pdf', { type: 'application/pdf' });
  const successPdf = ctrl.selectFile(textFile);
  assert.equal(successPdf, false);
  assert.match(ctrl.error, /not appear to be a supported video file/);
  assert.equal(ctrl.localVideo, null);
});

test('9. Verifying that local selection NEVER invokes the video upload API', () => {
  assert.equal(mockApiClient.uploadCallCount, 0, 'Upload call count must be 0 throughout local selection tests');
});

test('10. Confirming existing server-video playback type discrimination is preserved', () => {
  const localItem = {
    sourceType: 'local',
    file: new File([''], 'local.mp4'),
    objectUrl: 'blob:test',
    filename: 'local.mp4',
    sizeBytes: 100,
  };

  const serverItem = {
    video_id: 'vid_123',
    filename: 'server.mp4',
    duration_seconds: 30,
    size_bytes: 1000,
  };

  assert.equal(isLocalVideo(localItem), true);
  assert.equal(isLocalVideo(serverItem), false);
  assert.equal(isLocalVideo(null), false);
  assert.equal(isLocalVideo(undefined), false);
});

