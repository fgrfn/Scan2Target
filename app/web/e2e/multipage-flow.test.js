import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = 4174;
const origin = `http://127.0.0.1:${port}`;
let server;
let browser;
let serverOutput = '';

async function waitForServer() {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error(`Vite preview server exited with code ${server.exitCode}\n${serverOutput}`);
    }
    try {
      const response = await fetch(origin);
      if (response.ok) return;
    } catch {
      // Vite is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('Vite test server did not start');
}

before(async () => {
  const vite = path.join(root, 'node_modules', 'vite', 'bin', 'vite.js');
  server = spawn(process.execPath, [vite, 'preview', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
    cwd: root,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  server.stdout.on('data', (chunk) => { serverOutput += chunk.toString(); });
  server.stderr.on('data', (chunk) => { serverOutput += chunk.toString(); });
  await waitForServer();
  browser = await chromium.launch({ headless: true });
});

after(async () => {
  await browser?.close();
  server?.kill();
});

test('captures two interactive ADF pages and finalizes one optimized PDF', async () => {
  const context = await browser.newContext({ serviceWorkers: 'block' });
  const page = await context.newPage();
  const browserErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`));
  await page.addInitScript(() => localStorage.setItem('scan2target_lang', 'en'));
  let captureCount = 0;
  let finalizePayload = null;
  const jpeg = Buffer.from(
    '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/EB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/EB//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EB//2Q==',
    'base64'
  );

  const session = () => ({
    id: 'session-1', device_id: 'scanner-1', profile_id: 'document_300', target_id: 'archive',
    source: 'ADF', capture_mode: 'interactive', status: 'active', options: {},
    pages: Array.from({ length: captureCount }, (_, index) => ({
      id: `page-${index + 1}`, position: index + 1,
      preview_url: `/api/v1/scan/sessions/session-1/pages/page-${index + 1}/image`,
      created_at: '2026-07-21T12:00:00+00:00'
    })),
    created_at: '2026-07-21T12:00:00+00:00', updated_at: '2026-07-21T12:00:00+00:00'
  });

  await page.route('**/*', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (!pathname.startsWith('/api/v1/')) {
      await route.continue();
      return;
    }
    if (pathname.includes('/pages/') && pathname.endsWith('/image')) {
      await route.fulfill({ status: 200, contentType: 'image/jpeg', body: jpeg });
    } else if (pathname === '/api/v1/scan/sessions' && request.method() === 'GET') {
      await route.fulfill({ json: [] });
    } else if (pathname === '/api/v1/scan/sessions' && request.method() === 'POST') {
      await route.fulfill({ status: 201, json: session() });
    } else if (pathname.endsWith('/capture')) {
      captureCount += 1;
      await route.fulfill({ json: session() });
    } else if (pathname.endsWith('/finalize')) {
      finalizePayload = request.postDataJSON();
      await route.fulfill({ json: { job_id: 'job-1', status: 'completed' } });
    } else if (pathname === '/api/v1/devices') {
      await route.fulfill({ json: [{ id: 'scanner-1', name: 'Test scanner', is_favorite: true }] });
    } else if (pathname === '/api/v1/targets') {
      await route.fulfill({ json: [{ id: 'archive', name: 'Archive', enabled: true, is_favorite: true }] });
    } else if (pathname === '/api/v1/scan/profiles') {
      await route.fulfill({ json: [{ id: 'document_300', name: 'Document 300', description: 'document' }] });
    } else if (pathname === '/api/v1/auth/config') {
      await route.fulfill({ json: { enabled: false, setup_required: false } });
    } else if (pathname === '/api/v1/version') {
      await route.fulfill({ json: { version: 'test' } });
    } else if (pathname.startsWith('/api/v1/stats/')) {
      await route.fulfill({ json: pathname.endsWith('/overview') ? {} : [] });
    } else {
      await route.fulfill({ json: [] });
    }
  });

  await page.goto(origin, { waitUntil: 'networkidle' });
  const feederButton = page.getByRole('button', { name: /Document feeder/ });
  try {
    await feederButton.click();
  } catch (error) {
    const body = (await page.locator('body').innerText()).slice(0, 2_000);
    throw new Error(`${error.message}\nPage content:\n${body}\nBrowser errors:\n${browserErrors.join('\n')}\nServer output:\n${serverOutput}`);
  }
  await page.getByRole('button', { name: /Ask after every page/ }).click();
  await page.getByRole('button', { name: 'Start scan' }).click();
  await page.getByRole('heading', { name: 'Would you like to scan another page?' }).waitFor();
  await page.getByRole('button', { name: 'Yes, scan another page' }).click();
  await page.getByText('2 pages captured').waitFor();
  await page.getByRole('button', { name: 'No, create PDF' }).click();
  await page.getByLabel('Filename').fill('Invoices July');
  await page.getByText('Create searchable text with OCR').click();
  await page.getByText('Archive as PDF/A-2').click();
  await page.getByRole('button', { name: 'Save' }).click();

  await page.waitForFunction(() => document.body.textContent.includes('Scan was processed'));
  assert.equal(captureCount, 2);
  assert.equal(finalizePayload.filename_prefix, 'Invoices July');
  assert.equal(finalizePayload.optimize, true);
  assert.equal(finalizePayload.ocr, true);
  assert.equal(finalizePayload.pdfa, true);
  await context.close();
});
