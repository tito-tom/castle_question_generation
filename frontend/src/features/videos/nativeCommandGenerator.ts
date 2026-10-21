/**
 * CASTLE QA Studio - Native FFmpeg Command Generator
 *
 * Generates secure, platform-specific native FFmpeg commands and standalone scripts
 * for Windows PowerShell, Windows CMD, and Linux/macOS Bash.
 *
 * Implements strict argument sanitization and escaping to prevent command injection,
 * variable expansion, option injection (hyphen prefix), and silent overwriting.
 */

import { formatTimestamp } from './timestampUtils';

export type SupportedShell = 'powershell' | 'cmd' | 'bash';
export type NativeExtractionMode = 'frame_accurate' | 'fast_copy';

export interface NativeCommandOptions {
  sourceFilename: string;
  sourcePathPlaceholder?: string;
  startSeconds: number;
  endSeconds: number;
  mode: NativeExtractionMode;
  customOutputFilename?: string;
}

export interface GeneratedNativeCommand {
  shell: SupportedShell;
  mode: NativeExtractionMode;
  commandLine: string;
  scriptContent: string;
  scriptExtension: string;
  outputFilename: string;
  sourcePlaceholder: string;
  isFrameAccurate: boolean;
  keyframeWarning?: string;
}

/**
 * Strip control characters, newlines, and carriage returns that could break shell syntax.
 */
export function stripControlChars(val: string): string {
  return val.replace(/[\r\n\x00-\x1f\x7f]/g, '').trim();
}

/**
 * Ensure a CLI path argument does not start with a hyphen, which could be misparsed as an option/flag.
 */
export function ensureSafeCliPath(pathStr: string, isWindows: boolean = false): string {
  const clean = stripControlChars(pathStr);
  if (clean.startsWith('-')) {
    return isWindows ? `.\\${clean}` : `./${clean}`;
  }
  return clean;
}

/**
 * Sanitize a string for safe inclusion in filenames.
 * Strips path traversal characters, directory parts, and control chars.
 * Retains Unicode alphanumeric characters, underscores, dashes, and dots.
 * Strips leading hyphens so the output filename cannot be mistaken for a command-line flag.
 */
export function sanitizeFilename(name: string, defaultExt = 'mp4'): string {
  if (!name) return `clip.${defaultExt}`;
  // Strip directory paths and leading traversal dots
  const base = name.replace(/^.*[\\/]/, '').replace(/^\.+/, '').trim();
  // Keep unicode alphanumeric characters, dots, dashes, and underscores
  const safe = base
    .replace(/[^\p{L}\p{N}._-]/gu, '_')
    .replace(/_{2,}/g, '_');
  // Strip leading hyphens or underscores to prevent option injection
  const withoutLeadingHyphen = safe.replace(/^[-_]+/, '');
  const clean = withoutLeadingHyphen.replace(/\.[^.]+$/, '');
  const finalBase = clean || 'clip';
  return `${finalBase}.${defaultExt}`;
}

/**
 * Format timestamp for safe inclusion in filenames (e.g. 00-01-12).
 */
export function formatTimestampForFile(seconds: number): string {
  const ts = formatTimestamp(seconds); // HH:MM:SS.mmm
  return ts.replace(/:/g, '-').replace(/\.\d+$/, '');
}

/**
 * Escape an argument safely for Windows PowerShell.
 * Single quotes in PowerShell prevent any parameter or variable expansion ($var, `cmd, $(expr)).
 * Single quotes inside the string are escaped by doubling them ('').
 * Control chars and newlines are stripped, and leading hyphens prefixed with .\
 */
export function escapePowerShellArg(arg: string): string {
  const safePath = ensureSafeCliPath(arg, true);
  return `'${safePath.replace(/'/g, "''")}'`;
}

/**
 * Escape an argument safely for Windows CMD (Command Prompt).
 * Encloses in double quotes and strips control characters.
 * When forScript is true (in .bat files), percent signs % are escaped as %% to prevent variable expansion.
 * Leading hyphens are prefixed with .\ to prevent option injection.
 */
export function escapeCmdArg(arg: string, forScript: boolean = false): string {
  const safePath = ensureSafeCliPath(arg, true);
  const escapedQuotes = safePath.replace(/"/g, '""');
  const escapedPercent = forScript ? escapedQuotes.replace(/%/g, '%%') : escapedQuotes;
  return `"${escapedPercent}"`;
}

/**
 * Escape an argument safely for Linux/macOS Bash.
 * Single quotes prevent all variable expansions ($var, `cmd`, $(expr)).
 * Single quotes inside are escaped using '\'' sequence.
 * Control chars and newlines are stripped, and leading hyphens prefixed with ./
 */
export function escapeBashArg(arg: string): string {
  const safePath = ensureSafeCliPath(arg, false);
  return `'${safePath.replace(/'/g, "'\\''")}'`;
}

/**
 * Generate platform-specific FFmpeg commands and downloadable scripts.
 * Note: -y is intentionally omitted to avoid silently overwriting existing output files.
 */
export function generateNativeCommand(
  shell: SupportedShell,
  options: NativeCommandOptions
): GeneratedNativeCommand {
  const {
    sourceFilename,
    sourcePathPlaceholder,
    startSeconds,
    endSeconds,
    mode,
    customOutputFilename,
  } = options;

  const startFormatted = formatTimestamp(startSeconds);
  const endFormatted = formatTimestamp(endSeconds);
  const duration = Math.max(0, endSeconds - startSeconds);

  // Generate clean default output filename
  const baseName = sourceFilename.replace(/\.[^/.]+$/, '');
  const startTag = formatTimestampForFile(startSeconds);
  const endTag = formatTimestampForFile(endSeconds);
  const defaultOutputName = `clip_${sanitizeFilename(baseName).replace(/\.mp4$/, '')}_${startTag}_to_${endTag}.mp4`;
  const outputFilename = customOutputFilename ? sanitizeFilename(customOutputFilename) : defaultOutputName;

  const rawInput = sourcePathPlaceholder?.trim() || sourceFilename || 'input_video.mp4';
  const isFrameAccurate = mode === 'frame_accurate';

  let escapedInput = '';
  let escapedOutput = '';
  let commandLine = '';
  let scriptContent = '';
  let scriptExtension = '';

  const keyframeWarning = !isFrameAccurate
    ? 'Fast stream copy (-c copy) snaps to the nearest keyframe boundary (5.0s GOP in CASTLE recordings). Duration and boundaries may vary by ±2.5s.'
    : undefined;

  // Encoder parameters
  const codecArgs = isFrameAccurate
    ? '-c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k'
    : '-c copy -avoid_negative_ts make_zero';

  if (shell === 'powershell') {
    escapedInput = escapePowerShellArg(rawInput);
    escapedOutput = escapePowerShellArg(outputFilename);
    scriptExtension = 'ps1';

    // Note: -y omitted to prevent silent overwrite of existing clips
    commandLine = `ffmpeg -ss ${startFormatted} -to ${endFormatted} -i ${escapedInput} ${codecArgs} ${escapedOutput}`;

    scriptContent = [
      '# CASTLE QA Studio - Native Video Clip Extraction Script (PowerShell)',
      `# Source Video   : ${sourceFilename}`,
      `# Target Interval: ${startFormatted} -> ${endFormatted} (${duration.toFixed(1)}s)`,
      `# Mode           : ${isFrameAccurate ? 'Frame-Accurate Re-encode' : 'Fast Keyframe Copy'}`,
      '# Overwrite      : Prompt (avoiding silent overwrite)',
      keyframeWarning ? `# Note           : ${keyframeWarning}` : '',
      '',
      `Write-Host "Extracting short clip from ${sourceFilename}..." -ForegroundColor Cyan`,
      commandLine,
      'if ($LASTEXITCODE -eq 0) {',
      `    Write-Host "Extraction completed successfully: ${outputFilename}" -ForegroundColor Green`,
      '} else {',
      '    Write-Host "Extraction failed. Ensure ffmpeg is installed and available in PATH." -ForegroundColor Red',
      '}',
      '',
    ].filter(Boolean).join('\n');
  } else if (shell === 'cmd') {
    escapedInput = escapeCmdArg(rawInput, false);
    escapedOutput = escapeCmdArg(outputFilename, false);
    const scriptEscapedInput = escapeCmdArg(rawInput, true);
    const scriptEscapedOutput = escapeCmdArg(outputFilename, true);
    scriptExtension = 'bat';

    commandLine = `ffmpeg -ss ${startFormatted} -to ${endFormatted} -i ${escapedInput} ${codecArgs} ${escapedOutput}`;
    const scriptCommandLine = `ffmpeg -ss ${startFormatted} -to ${endFormatted} -i ${scriptEscapedInput} ${codecArgs} ${scriptEscapedOutput}`;

    scriptContent = [
      '@echo off',
      'REM CASTLE QA Studio - Native Video Clip Extraction Script (Windows CMD)',
      `REM Source Video   : ${sourceFilename}`,
      `REM Target Interval: ${startFormatted} -> ${endFormatted} (${duration.toFixed(1)}s)`,
      `REM Mode           : ${isFrameAccurate ? 'Frame-Accurate Re-encode' : 'Fast Keyframe Copy'}`,
      'REM Overwrite      : Prompt (avoiding silent overwrite)',
      keyframeWarning ? `REM Note           : ${keyframeWarning}` : '',
      '',
      `echo Extracting short clip from ${sourceFilename}...`,
      scriptCommandLine,
      'if %ERRORLEVEL% EQU 0 (',
      `    echo Extraction completed successfully: ${outputFilename}`,
      ') else (',
      '    echo Extraction failed. Ensure ffmpeg is installed and available in PATH.',
      ')',
      'pause',
      '',
    ].filter(Boolean).join('\n');
  } else {
    // Linux / macOS Bash
    escapedInput = escapeBashArg(rawInput);
    escapedOutput = escapeBashArg(outputFilename);
    scriptExtension = 'sh';

    commandLine = `ffmpeg -ss ${startFormatted} -to ${endFormatted} -i ${escapedInput} ${codecArgs} ${escapedOutput}`;

    scriptContent = [
      '#!/usr/bin/env bash',
      '# CASTLE QA Studio - Native Video Clip Extraction Script (Bash)',
      `# Source Video   : ${sourceFilename}`,
      `# Target Interval: ${startFormatted} -> ${endFormatted} (${duration.toFixed(1)}s)`,
      `# Mode           : ${isFrameAccurate ? 'Frame-Accurate Re-encode' : 'Fast Keyframe Copy'}`,
      '# Overwrite      : Prompt (avoiding silent overwrite)',
      keyframeWarning ? `# Note           : ${keyframeWarning}` : '',
      'set -e',
      '',
      `echo "Extracting short clip from ${sourceFilename}..."`,
      commandLine,
      `echo "Extraction completed successfully: ${outputFilename}"`,
      '',
    ].filter(Boolean).join('\n');
  }

  return {
    shell,
    mode,
    commandLine,
    scriptContent,
    scriptExtension,
    outputFilename,
    sourcePlaceholder: rawInput,
    isFrameAccurate,
    keyframeWarning,
  };
}
