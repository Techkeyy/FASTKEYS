const { chromium } = require(process.env.FASTKEYS_PLAYWRIGHT_MODULE||'playwright-core');
const fs = require('fs');
;(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.FASTKEYS_BROWSER });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  const chooser = page.waitForEvent('filechooser');
  await page.locator('.final-cta .js-choose-audio').click();
  await chooser;
  const fixture = { duration: 8, key: 'C Major', chord_progression: [{ chord: 'C', start: 0, end: 8 }], melody_notes: [{ midi: 60, start: 0, end: 8 }] };
  await page.route('**/samples/fixture_pop_C.wav', route => route.fulfill({ path: 'fixture_pop_C.wav', contentType: 'audio/wav' }));
  await page.route('**/api/analyze', route => route.fulfill({ json: fixture }));
  await page.locator('.final-cta .js-try-sample').click();
  await page.locator('#screenWorkspace').waitFor({ state: 'visible', timeout: 30000 });
  const result = { finalChooseOpensFileChooser: true, finalSampleReachesWorkspace: await page.locator('#screenWorkspace').isVisible(), key: await page.locator('#wsKeyDisplay').textContent() };
  fs.writeFileSync('evidence/landing-story-actions.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
