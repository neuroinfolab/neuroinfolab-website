import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const URL = process.argv[2] ?? 'http://localhost:4321/';
const OUT = process.argv[3] ?? 'publications-review/screenshots';
mkdirSync(OUT, { recursive: true });

async function launch() {
  if (process.env.PLAYWRIGHT_CHANNEL) {
    return chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL });
  }
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return chromium.launch();
  }
}

const browser = await launch();

for (const view of [
  { name: 'desktop', width: 1440, height: 900, mobile: false },
  { name: 'mobile', width: 390, height: 844, mobile: true },
]) {
  const context = await browser.newContext({
    viewport: { width: view.width, height: view.height },
    deviceScaleFactor: 1,
    isMobile: view.mobile,
    hasTouch: view.mobile,
  });
  const page = await context.newPage();
  const errors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('pageerror', (error) => errors.push(error.message));

  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.querySelectorAll('video').forEach((video) => video.pause()));

  // Walk the page so lazy images and reveal observers settle before capture.
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < height; y += Math.round(view.height * 0.75)) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(60);
  }

  const publications = page.locator('#publications');
  await publications.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  const headerStyle = await page.addStyleTag({
    content: '.site-header, .skip { display: none !important; }',
  });
  await publications.screenshot({ path: `${OUT}/${view.name}-publications.png` });
  await headerStyle.evaluate((element) => element.remove());
  await page.screenshot({
    path: `${OUT}/${view.name}-full.jpg`,
    fullPage: true,
    type: 'jpeg',
    quality: 80,
  });

  console.log(
    `${view.name}: ${view.width}x${view.height}, ${height}px tall, ` +
      `${errors.length ? `${errors.length} console errors` : 'no console errors'}`,
  );
  await context.close();
}

await browser.close();
