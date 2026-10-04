const { chromium } = require('C:/Users/HomePC/Desktop/CLINCH-DEMO/node_modules/playwright-core');
;(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Users/HomePC/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe' });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  const result = await page.evaluate(() => ({
    root: { innerWidth, clientWidth: document.documentElement.clientWidth, htmlScrollWidth: document.documentElement.scrollWidth, bodyScrollWidth: document.body.scrollWidth, bodyClientWidth: document.body.clientWidth },
    hiddenReveals: [...document.querySelectorAll('.reveal:not(.is-visible)')].map(el => ({ cls: el.className, text: el.textContent.trim().slice(0, 70) })),
    pseudo: [...document.querySelectorAll('*')].flatMap(el => ['::before','::after'].map(pseudo => ({
      tag: el.tagName, cls: el.className?.toString(), id: el.id, pseudo,
      content: getComputedStyle(el, pseudo).content,
      width: getComputedStyle(el, pseudo).width,
      left: getComputedStyle(el, pseudo).left,
      right: getComputedStyle(el, pseudo).right,
      position: getComputedStyle(el, pseudo).position,
      transform: getComputedStyle(el, pseudo).transform,
    }))).filter(item => item.content && item.content !== 'none'),
    elements: [...document.querySelectorAll('*')].map(el => {
    const r = el.getBoundingClientRect();
    return { tag: el.tagName, cls: el.className?.toString(), id: el.id, left: r.left, right: r.right, width: r.width, clientWidth: el.clientWidth, scrollWidth: el.scrollWidth };
  }).filter(item => item.left < -1 || item.right > innerWidth + 1 || item.scrollWidth > item.clientWidth + 1).sort((a, b) => Math.max(b.right, b.scrollWidth) - Math.max(a.right, a.scrollWidth)).slice(0, 40)
  }));
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})();
