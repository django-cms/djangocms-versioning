const { test, expect } = require('@playwright/test');
const http = require('http');
const fs = require('fs');
const path = require('path');

/**
 * Simple static server for E2E
 */
function createServer(rootDir) {
  const server = http.createServer((req, res) => {
    if (req.url === '/api/v1') {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body><div id="content">Published V1</div></body></html>');
      return;
    }
    if (req.url === '/api/v2') {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body><div id="content">Draft V2</div></body></html>');
      return;
    }
    // static files
    let rawPath = decodeURIComponent(req.url.split('?')[0]);
    let resolvedPath = path.resolve(rootDir, '.' + rawPath); // prevent rootDir + "/etc/passwd"
    let filePath;
    try {
      filePath = fs.realpathSync(resolvedPath);
    } catch (e) {
      res.writeHead(404);
      res.end('Not Found');
      return;
    }
    if (!filePath.startsWith(rootDir)) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }
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

async function collectCoverage(page) {
  const coverage = await page.evaluate(() => window.__coverage__);
  if (coverage) {
    const outDir = path.join(process.cwd(), '.nyc_output');
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir);
    const outPath = path.join(outDir, `playwright-coverage-${Date.now()}.json`);
    fs.writeFileSync(outPath, JSON.stringify(coverage));
  }
}

// Build must be done before running these tests: npm run bundle:coverage

test('renders controls and toggles views', async ({ page }) => {
  await page.goto('/tests/e2e/fixtures/versioning.html');

  // Controls appear
  const controls = page.locator('.cms-versioning-controls');
  await expect(controls).toBeVisible();

  // Click visual, then source
  const visualBtn = page.locator('.js-cms-versioning-control-visual');
  const sourceBtn = page.locator('.js-cms-versioning-control-source');

  await visualBtn.click();
  await expect(visualBtn).toHaveClass(/cms-btn-active/);

  await sourceBtn.click();
  await expect(sourceBtn).toHaveClass(/cms-btn-active/);

  // Iframe exists
  const frame = page.locator('iframe.js-cms-versioning-diff-frame');
  await expect(frame).toHaveCount(1);

  await collectCoverage(page);
});
