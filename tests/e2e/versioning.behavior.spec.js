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

// Reuse iframe and fetch caching: clicking Visual twice should not cause >2 fetches overall
// then clicking Source should reuse cached markup (no extra fetches)
test('iframe reuse and cached fetches', async ({ page }) => {
  await withFetchCounter(page);
  await page.goto('/tests/e2e/fixtures/versioning.html');

  const visualBtn = page.locator('.js-cms-versioning-control-visual');
  await visualBtn.click();
  await visualBtn.click();

  const iframeCount = await page.locator('iframe.js-cms-versioning-diff-frame').count();
  expect(iframeCount).toBe(1);

  const fetchCountAfterVisual = await page.evaluate(() => window.__fetchCount());
  // two fetches: v1 and v2
  expect(fetchCountAfterVisual).toBe(2);

  const sourceBtn = page.locator('.js-cms-versioning-control-source');
  await sourceBtn.click();

  const fetchCountAfterSource = await page.evaluate(() => window.__fetchCount());
  // still 2 if cache worked
  expect(fetchCountAfterSource).toBe(2);

  await collectCoverage(page);
});

// switchVersion branches: no query -> ?compare_to, has ? -> &compare_to, has compare_to -> replace
for (const { name, url, expected } of [
  { name: 'no query', url: '/tests/e2e/fixtures/versioning.html', expected: /compare_to=2/ },
  { name: 'with query', url: '/tests/e2e/fixtures/versioning.html?foo=1', expected: /foo=1&compare_to=2/ },
  { name: 'replace compare_to', url: '/tests/e2e/fixtures/versioning.html?compare_to=9', expected: /compare_to=2/ },
]) {
  test(`switchVersion ${name}`, async ({ page }) => {
    await page.goto(url);
    const selector = page.locator('.js-cms-versioning-version');
    await selector.selectOption('2');
    await page.waitForURL((u) => expected.test(u.toString()));
  });
}

// breakout of iframe: parent page with iframe should navigate to iframe URL
test('breakOutOfAnIframe navigates top to iframe url', async ({ page }) => {
  await page.goto('/tests/e2e/fixtures/host.html');
  await page.waitForURL(/\/tests\/e2e\/fixtures\/versioning\.html/);
});

// controls visible toggles display from none to block
test('controls button group becomes visible', async ({ page }) => {
  await page.goto('/tests/e2e/fixtures/versioning.html');
  const btnGroup = page.locator('.cms-btn-group');
  await expect(btnGroup).toBeVisible();
  const display = await btnGroup.evaluate(el => getComputedStyle(el).display);
  expect(display).toBe('block');
});

// Source view injects script and style into iframe
test('source view injects script and style in iframe', async ({ page }) => {
  await page.goto('/tests/e2e/fixtures/versioning.html');
  const sourceBtn = page.locator('.js-cms-versioning-control-source');
  await sourceBtn.click();

  const frameHandle = await page.locator('iframe.js-cms-versioning-diff-frame').elementHandle();
  const frame = await frameHandle.contentFrame();

  // Wait a bit for srcdoc to be applied and DOM to render
  await frame.waitForSelector('script', { state: 'attached' });
  await frame.waitForSelector('style', { state: 'attached' });

  const scriptCount = await frame.locator('script').count();
  const styleCount = await frame.locator('style').count();

  expect(scriptCount).toBeGreaterThan(0);
  expect(styleCount).toBeGreaterThan(0);
});
