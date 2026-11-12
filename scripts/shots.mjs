import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const OUT = process.argv[2] ?? 'shots';
const URL = process.argv[3] ?? 'http://localhost:4321/';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });

const shots = [
  { name: 'desktop', width: 1440, height: 1000, mobile: false },
  { name: 'phone', width: 390, height: 844, mobile: true },
];

for (const s of shots) {
  const context = await browser.newContext({
    viewport: { width: s.width, height: s.height },
    deviceScaleFactor: 2,
    isMobile: s.mobile,
    hasTouch: s.mobile,
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  await page.goto(URL, { waitUntil: 'networkidle' });

  // walk the page so lazy images and reveal observers fire before we capture
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < height; y += Math.round(s.height * 0.75)) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(90);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(700);
  await page.evaluate(() => document.querySelectorAll('video').forEach((v) => v.pause()));

  await page.screenshot({ path: `${OUT}/${s.name}-fold.png` });
  await page.screenshot({ path: `${OUT}/${s.name}-full.png`, fullPage: true });
  console.log(`${s.name}: ${s.width}x${s.height}, full height ${height}px`);
  await context.close();
}

const c = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const p = await c.newPage();
await p.goto(URL, { waitUntil: 'networkidle' });
await p.waitForTimeout(900);
await p.screenshot({ path: `${OUT}/hero.png` });
await c.close();

await browser.close();
