import { defineConfig, devices } from '@playwright/test';
import fs from 'fs';

// Resolve installed Edge path on Windows
const edgePaths = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
];
const edgeExecutable = edgePaths.find((p) => fs.existsSync(p));
const bravePaths = [
  'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
  'C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
];
const braveExecutable = process.env.PLAYWRIGHT_BRAVE_PATH || bravePaths.find((p) => fs.existsSync(p));
const selectedBrowser = process.env.PLAYWRIGHT_BROWSER?.toLowerCase();
if (selectedBrowser === 'brave' && (!braveExecutable || !fs.existsSync(braveExecutable))) {
  throw new Error('PLAYWRIGHT_BROWSER=brave was requested, but no Brave executable was found. Set PLAYWRIGHT_BRAVE_PATH to brave.exe.');
}
const browserProject = selectedBrowser === 'brave'
  ? {
      name: 'brave',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: { executablePath: braveExecutable },
      },
    }
  : {
      name: 'msedge',
      use: {
        ...devices['Desktop Edge'],
        channel: 'msedge',
        launchOptions: edgeExecutable ? { executablePath: edgeExecutable } : undefined,
      },
    };

export default defineConfig({
  testDir: './e2e',
  globalTeardown: './e2e/global-teardown.mjs',
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  expect: {
    timeout: 15000,
  },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  webServer: {
    command: 'node e2e/test-stack.mjs',
    url: 'http://127.0.0.1:3000',
    timeout: 180000,
    reuseExistingServer: false,
    stdout: 'pipe',
    stderr: 'pipe',
  },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    actionTimeout: 15000,
    navigationTimeout: 20000,
    headless: true,
    permissions: ['clipboard-read', 'clipboard-write'],
    launchOptions: edgeExecutable
      ? {
          executablePath: edgeExecutable,
        }
      : undefined,
  },
  projects: [browserProject],
});
