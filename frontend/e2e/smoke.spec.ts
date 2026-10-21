import { test, expect } from '@playwright/test';

test('Playwright can launch Edge', async ({ page }) => {
  await page.goto('data:text/html,<html><body><h1>Playwright Edge Launch Smoke Test</h1></body></html>');
  const h1 = page.locator('h1');
  await expect(h1).toHaveText('Playwright Edge Launch Smoke Test');
});

