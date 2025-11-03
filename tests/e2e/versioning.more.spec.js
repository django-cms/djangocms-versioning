const { test, expect } = require('@playwright/test');
const http = require('http');
const fs = require('fs');
const path = require('path');

function createServer(rootDir) {
  const server = http.createServer((req, res) => {
    if (req.url.startsWith('/api/v1')) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body><div id="content">Published V1</div></body></html>');
      return;
    }
    if (req.url.startsWith('/api/v2')) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body><div id="content">Draft V2</div></body></html>');
      return;
    }
    const filePath = path.join(rootDir, decodeURIComponent(req.url.split('?')[0]));
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('Not Found');
        return;
      }
      const ext = path.extname(filePath);
      const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css' };
      res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream' });
      res.end(data);
    });
  });
  return server;
}

let server;
const PORT = 8089;

test.beforeAll(async () => {
  server = createServer(process.cwd());
  await new Promise((resolve) => server.listen(PORT, resolve));
});

test.afterAll(async () => {
  await new Promise((resolve) => server.close(resolve));
});

async function withFetchCounter(page) {
  await page.addInitScript(() => {
    const origFetch = window.fetch;
    let count = 0;
    window.__fetchCount = () => count;
    window.fetch = (...args) => {
      count += 1;
      return origFetch(...args);
    };
  });
}

async function collectCoverage(page) {
  const coverage = await page.evaluate(() => window.__coverage__);
  if (coverage) {
    const outDir = path.join(process.cwd(), '.nyc_output');
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir);
    const outPath = path.join(outDir, `playwright-coverage-${Date.now()}.json`);
    fs.writeFileSync(outPath, JSON.stringify(coverage));
  }
}

// Loader shows during first load, then hides again
test('loader shows and hides around loadMarkup', async ({ page }) => {
  await page.goto('/tests/e2e/fixtures/versioning.html');
  await page.locator('.js-cms-versioning-control-visual').click();
  // loader bar is attached (may be hidden during animation)
  await page.waitForSelector('.cms-loading-bar', { state: 'attached' });
  // eventually it disappears
  await page.waitForSelector('.cms-loading-bar', { state: 'detached' });
  await collectCoverage(page);
});

// Clicking already-active button should be a no-op
test('clicking active button is no-op', async ({ page }) => {
  await withFetchCounter(page);
  await page.goto('/tests/e2e/fixtures/versioning.html');
  const visual = page.locator('.js-cms-versioning-control-visual');
  await visual.click();
  const countAfterFirst = await page.evaluate(() => window.__fetchCount());
  await visual.click();
  const countAfterSecond = await page.evaluate(() => window.__fetchCount());
  expect(countAfterSecond).toBe(countAfterFirst);
});

// Clicking already-active source button is a no-op
test('clicking active source button is no-op', async ({ page }) => {
  await withFetchCounter(page);
  await page.goto('/tests/e2e/fixtures/versioning.html');
  const source = page.locator('.js-cms-versioning-control-source');
  // Ensure source becomes active once
  const waitChunk = page.waitForResponse(resp => resp.url().includes('/djangocms_versioning/static/djangocms_versioning/js/dist/bundle.prettydiff.min.js') && resp.ok());
  await source.click();
  await waitChunk;
  const fetchAfterFirst = await page.evaluate(() => window.__fetchCount());
  // Now clicking again should not trigger another chunk load; use a short timeout
  let secondChunkLoaded = false;
  try {
    await page.waitForResponse(resp => resp.url().includes('/djangocms_versioning/static/djangocms_versioning/js/dist/bundle.prettydiff.min.js') && resp.ok(), { timeout: 500 });
    secondChunkLoaded = true;
  } catch (e) {
    secondChunkLoaded = false;
  }
  const fetchAfterSecond = await page.evaluate(() => window.__fetchCount());
  expect(secondChunkLoaded).toBe(false);
  expect(fetchAfterSecond).toBe(fetchAfterFirst); // no additional fetches (cached)
});

// CMS Sideframe close is invoked when available
test.skip('CMS sideframe close is called when available', async ({ page }) => {
  await page.addInitScript(() => {
    window.top.__closed = false;
    window.top.CMS = { API: { Sideframe: { close: () => { window.top.__closed = true; } } } };
  });
  await page.goto('/tests/e2e/fixtures/versioning.html');
  await page.waitForFunction(() => window.top.__closed === true);
});

// When v2_url is missing, controls stay hidden and no iframe is injected
test('no v2_url -> controls stay hidden and no iframe', async ({ page }) => {
  await page.goto('/tests/e2e/fixtures/versioning.v1-only.html');
  // button group stays hidden because showControls() guard fails
  const btnGroup = page.locator('.cms-btn-group');
  const display = await btnGroup.evaluate(el => getComputedStyle(el).display);
  expect(display).toBe('none');
  // and no iframe is created automatically
  await expect(page.locator('iframe.js-cms-versioning-diff-frame')).toHaveCount(0);
});
