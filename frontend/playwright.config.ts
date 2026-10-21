import { defineConfig, devices } from '@playwright/test';
import fs from 'fs';

// Resolve installed Edge path on Windows
const edgePaths = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
];
const edgeExecutable = edgePaths.find((p) => fs.existsSync(p));

export default defineConfig({
  testDir: './e2e',
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
  projects: [
    {
      name: 'msedge',
      use: {
        ...devices['Desktop Edge'],
        channel: 'msedge',
        launchOptions: edgeExecutable ? { executablePath: edgeExecutable } : undefined,
      },
    },
  ],
});
