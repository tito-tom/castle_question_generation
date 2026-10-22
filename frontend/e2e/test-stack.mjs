import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = path.resolve(frontendDir, '..');
const runDir = await mkdtemp(path.join(frontendDir, '.playwright-e2e-'));
const composeProject = `castleqa-e2e-${path.basename(runDir).replace(/[^a-z0-9]/gi, '').toLowerCase()}`;
const overridePath = path.join(runDir, 'compose.override.yaml');
const statePath = path.join(frontendDir, '.playwright-e2e-state.json');
const dataPath = path.join(runDir, 'data').replaceAll('\\', '/');
const sourcePath = path.join(repoRoot, 'backend', 'src').replaceAll('\\', '/');
let vite;
let shuttingDown = false;

const portServer = createServer();
portServer.listen(0, '127.0.0.1');
await once(portServer, 'listening');
const apiPort = portServer.address().port;
await new Promise((resolve, reject) => portServer.close((error) => error ? reject(error) : resolve()));
const environment = `      ENVIRONMENT: development\n      VIDEO_UNDERSTANDING_MODE: mock\n      CASTLE_ANALYSIS_DIR: /e2e-data/analysis\n      CASTLE_QUESTION_DIR: /e2e-data/questions/api_template\n      CASTLE_JOB_DB_PATH: /e2e-data/jobs/jobs.sqlite3\n      CASTLE_VIDEO_STORAGE_DIR: /e2e-data/videos\n      CASTLE_VIDEO_DIR: /e2e-data/videos\n      CASTLE_CLIPS_DIR: /e2e-data/clips\n      CASTLE_TEMP_CLIPS_DIR: /e2e-data/clips/temp_uploads\n      CASTLE_REVIEWS_DIR: /e2e-data/reviews\n`;
const mount = `      - type: bind\n        source: "${sourcePath}"\n        target: /app/src\n        read_only: true\n      - type: bind\n        source: "${dataPath}"\n        target: /e2e-data\n`;
const override = `services:\n  api:\n    image: castle-qa-api:latest\n    container_name: ${composeProject}-api\n    user: "0:0"\n    ports:\n      - "${apiPort}:8000"\n    environment:\n${environment}      PYTHONPATH: /app/src\n    volumes:\n${mount}  worker:\n    image: castle-qa-worker:latest\n    container_name: ${composeProject}-worker\n    user: "0:0"\n    environment:\n${environment}      PYTHONPATH: /app/src\n    volumes:\n${mount}    depends_on:\n      - api\n`;
await writeFile(overridePath, override, 'utf8');
await mkdir(path.join(runDir, 'data'), { recursive: true });
await writeFile(statePath, JSON.stringify({ runDir, composeProject, overridePath }), 'utf8');

const compose = (...args) => {
  const result = spawnSync('docker', ['compose', '-p', composeProject, '-f', overridePath, ...args], {
    cwd: repoRoot,
    stdio: 'inherit',
    env: process.env,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`docker compose ${args.join(' ')} failed (${result.status}).`);
};

const waitFor = async (url, label, timeoutMs = 120000) => {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    const controller = new AbortController();
    const requestTimeout = setTimeout(() => controller.abort(), 2000);
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (response.ok) return;
    } catch {}
    finally { clearTimeout(requestTimeout); }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for ${label} at ${url}.`);
};

const shutdown = async (code = 0) => {
  if (shuttingDown) return;
  console.log(`Shutting down E2E harness (${code})...`);
  shuttingDown = true;
  if (vite && vite.exitCode === null) vite.kill();
  try { compose('down', '--remove-orphans'); } catch (error) { console.error(error); code = 1; }
  try { await rm(runDir, { recursive: true, force: true }); } catch (error) { console.error(error); code = 1; }
  try { await rm(statePath, { force: true }); } catch (error) { console.error(error); code = 1; }
  process.exit(code);
};

process.on('SIGINT', () => shutdown(130));
process.on('SIGTERM', () => shutdown(143));
process.on('uncaughtException', (error) => { console.error(error); shutdown(1); });

try {
  console.log('Initializing isolated E2E database...');
  compose('run', '--rm', '--no-deps', 'api', 'python', '-m', 'alembic', '-c', 'alembic.ini', 'upgrade', 'head');
  console.log('Starting API and CPU mock worker...');
  compose('up', '-d', '--no-build', 'api', 'worker');
  await waitFor(`http://127.0.0.1:${apiPort}/api/v1/health`, 'FastAPI');
  console.log('FastAPI health check passed.');
  const logs = spawnSync('docker', ['logs', `${composeProject}-worker`], { encoding: 'utf8' });
  const workerLogs = `${logs.stdout || ''}${logs.stderr || ''}`;
  console.log(`Worker log check (exit ${logs.status}): ${workerLogs.includes('Worker started') ? 'started' : 'not started'}`);
  if (logs.status !== 0 || !workerLogs.includes('Worker started')) {
    throw new Error(`Mock worker failed to start or claim its queue. ${logs.stderr || logs.stdout}`);
  }

  vite = spawn(process.execPath, [path.join(frontendDir, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '3000', '--strictPort'], {
    cwd: frontendDir,
    stdio: 'inherit',
    env: { ...process.env, CASTLE_E2E_API_URL: `http://127.0.0.1:${apiPort}` },
  });
  vite.on('error', (error) => { console.error('Could not start Vite:', error); shutdown(1); });
  vite.on('exit', (code) => { if (!shuttingDown) shutdown(code === 0 ? 0 : 1); });
  console.log('Starting Vite frontend...');
  await waitFor('http://127.0.0.1:3000/', 'Vite frontend', 30000);
  console.log(`E2E services ready: API :${apiPort}, worker ${composeProject}-worker, frontend :3000`);
} catch (error) {
  console.error(error);
  await shutdown(1);
}
