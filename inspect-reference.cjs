const { chromium } = require('C:/Users/HomePC/Desktop/CLINCH-DEMO/node_modules/playwright-core');
const fs = require('node:fs');
(async () => {
 fs.mkdirSync('evidence', {recursive:true});
 const browser = await chromium.launch({headless:true, executablePath:'C:/Users/HomePC/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe'});
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 await page.goto('https://ballroom-eight.vercel.app/', {waitUntil:'networkidle',timeout:60000});
 await page.screenshot({path:'evidence/reference-desktop.png',fullPage:true});
 console.log((await page.locator('body').innerText()).slice(0,12000));
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'evidence/reference-mobile.png',fullPage:true});
 console.log('production health', await (await page.request.get('https://fastkeys.onrender.com/api/health',{timeout:60000})).text());
 await browser.close();
})();
