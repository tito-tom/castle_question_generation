import { spawnSync } from 'node:child_process';
import { access, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = path.resolve(frontendDir, '..');
const statePath = path.join(frontendDir, '.playwright-e2e-state.json');

export default async function globalTeardown() {
  let state;
  try {
    state = JSON.parse(await readFile(statePath, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }

  const runDir = path.resolve(state.runDir);
  const relativeRunDir = path.relative(frontendDir, runDir);
  if (!relativeRunDir.startsWith('.playwright-e2e-') || relativeRunDir.includes(path.sep)) {
    throw new Error(`Refusing to clean an unexpected E2E directory: ${runDir}`);
  }

  const overridePath = path.resolve(state.overridePath);
  if (path.dirname(overridePath) !== runDir || path.basename(overridePath) !== 'compose.override.yaml') {
    throw new Error(`Refusing to use an unexpected compose file: ${overridePath}`);
  }

  try {
    await access(overridePath);
    const result = spawnSync('docker', [
      'compose', '-p', state.composeProject, '-f', overridePath, 'down', '--remove-orphans',
    ], { cwd: repoRoot, stdio: 'inherit' });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`E2E docker compose cleanup failed (${result.status}).`);
  } finally {
    await rm(runDir, { recursive: true, force: true });
    await rm(statePath, { force: true });
  }
}
