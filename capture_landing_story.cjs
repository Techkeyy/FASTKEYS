const { chromium } = require('C:/Users/HomePC/Desktop/CLINCH-DEMO/node_modules/playwright-core');
const fs = require('fs');

const root = 'C:/Users/HomePC/Desktop/FASTKEYS';
const out = `${root}/evidence`;
fs.mkdirSync(out, { recursive: true });
;(async () => {
const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Users/HomePC/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe',
});

async function capture(viewport, prefix) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  await page.screenshot({ path: `${out}/${prefix}-initial.png`, fullPage: true });
  const sections = [
    ['hero', '#top'],
    ['problem', '.problem-section'],
    ['outputs', '.outputs-section'],
    ['preview', '.preview-section'],
    ['steps', '.steps-section'],
    ['transformation', '.transformation-section'],
    ['final', '.final-cta'],
  ];
  const sectionSnapshots = [];
  for (const [name, selector] of sections) {
    await page.locator(selector).scrollIntoViewIfNeeded();
    await page.waitForTimeout(700);
    await page.screenshot({ path: `${out}/${prefix}-${name}.png`, fullPage: false });
    sectionSnapshots.push({ name, visible: await page.locator(selector).evaluate(el => !!el.querySelector('.is-visible') || el.classList.contains('is-visible')) });
  }
  await page.locator('.output-row:last-child').scrollIntoViewIfNeeded();
  await page.waitForTimeout(700);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(700);
  await page.addStyleTag({ content: '.reveal{opacity:1!important;transform:none!important}.note-path,.transform-connectors path,.step svg{stroke-dashoffset:0!important}' });
  await page.screenshot({ path: `${out}/${prefix}-full.png`, fullPage: true });
  const metrics = await page.evaluate(() => ({
    viewport: { width: innerWidth, height: innerHeight },
    scrollWidth: document.documentElement.scrollWidth,
    bodyHeight: document.body.scrollHeight,
    revealCount: document.querySelectorAll('.reveal').length,
    visibleRevealCount: document.querySelectorAll('.reveal.is-visible').length,
    hiddenRevealLabels: [...document.querySelectorAll('.reveal:not(.is-visible)')].map(element => element.className),
    inlineSvgCount: document.querySelectorAll('#story svg').length,
    environment: getComputedStyle(document.querySelector('.environment')).backgroundImage,
    previewAnimation: getComputedStyle(document.querySelector('.preview-timeline span')).animationName,
    previewAnimationCss: getComputedStyle(document.querySelector('.preview-timeline span')).animation,
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    transform: getComputedStyle(document.querySelector('.environment')).transform,
    resources: performance.getEntriesByType('resource').map(entry => ({ name: entry.name, transferSize: entry.transferSize || 0 }))
      .filter(entry => ['/style.css', '/app.js', '/music.js', '/hero.jpg'].some(path => entry.name.endsWith(path))),
  }));
  await page.close();
  return { metrics, sectionSnapshots, errors };
}

async function captureReducedMotion() {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  const result = await page.evaluate(() => ({
    media: matchMedia('(prefers-reduced-motion: reduce)').matches,
    allRevealsVisible: [...document.querySelectorAll('.reveal')].every(element => getComputedStyle(element).opacity === '1' && getComputedStyle(element).transform === 'none'),
    environmentTransform: getComputedStyle(document.querySelector('.environment')).transform,
    transition: getComputedStyle(document.querySelector('.reveal')).transition,
    previewAnimation: getComputedStyle(document.querySelector('.preview-timeline span')).animationName,
    previewAnimationCss: getComputedStyle(document.querySelector('.preview-timeline span')).animation,
    scrollWidth: document.documentElement.scrollWidth,
    viewportWidth: innerWidth,
  }));
  await page.close();
  return result;
}

const desktop = await capture({ width: 1440, height: 1000 }, 'landing-story-desktop');
const mobile = await capture({ width: 390, height: 844 }, 'landing-story-mobile');
const reducedMotion = await captureReducedMotion();
const result = {
  desktop,
  mobile,
  reducedMotion,
  capturedAt: new Date().toISOString(),
};
fs.writeFileSync(`${out}/landing-story-proof.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
})();
