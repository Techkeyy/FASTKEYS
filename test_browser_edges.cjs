const {chromium}=require(process.env.FASTKEYS_PLAYWRIGHT_MODULE||'C:/Users/HomePC/Desktop/CLINCH-DEMO/node_modules/playwright-core');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.FASTKEYS_BROWSER||'C:/Users/HomePC/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe'});
 const page=await browser.newPage({viewport:{width:320,height:740}});const proof={};await page.goto('http://127.0.0.1:8000');
 proof.landing320=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
 // Replay a saved real inference response to exercise the browser without repeating inference.
 const data=JSON.parse(fs.readFileSync('evidence/pop-analysis.json'));
 await page.route('**/api/analyze',r=>r.fulfill({json:data}));await page.locator('#audioFileInput').setInputFiles('fixture_pop_C.wav');await page.locator('#screenWorkspace').waitFor({state:'visible'});
 proof.workspace320=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
 // Measure decoded audio samples, not just whether currentTime advances.
 await page.evaluate(async()=>{window.audioProbe={context:new AudioContext()};const p=window.audioProbe;p.source=p.context.createMediaElementSource(document.querySelector('audio'));p.analyser=p.context.createAnalyser();p.source.connect(p.analyser);p.analyser.connect(p.context.destination);await p.context.resume();});
 await page.click('#btnPlayPause');await page.waitForFunction(()=>document.querySelector('audio').currentTime>.5);
 proof.audio=await page.evaluate(()=>{const p=window.audioProbe,samples=new Float32Array(p.analyser.fftSize);p.analyser.getFloatTimeDomainData(samples);return {rms:Math.sqrt(samples.reduce((s,x)=>s+x*x,0)/samples.length),muted:document.querySelector('audio').muted,volume:document.querySelector('audio').volume,context:p.context.state,time:document.querySelector('audio').currentTime};});assert(proof.audio.rms>0.001);assert(!proof.audio.muted);await page.click('#btnPlayPause');
 await page.click('#btnNewSong');await page.unroute('**/api/analyze');
 await page.route('**/api/analyze',r=>r.fulfill({status:500,json:{detail:'internal failure'}}));await page.locator('#audioFileInput').setInputFiles('fixture_pop_C.wav');await page.locator('#screenFailed').waitFor({state:'visible'});proof.error=await page.locator('#failedReasonText').innerText();await page.screenshot({path:'evidence/error-mobile.png',fullPage:true});await page.unroute('**/api/analyze');
 await page.reload();await page.locator('#audioFileInput').setInputFiles({name:'bad.txt',mimeType:'text/plain',buffer:Buffer.from('not audio')});await page.locator('#screenFailed').waitFor({state:'visible'});proof.unsupported=await page.locator('#failedReasonText').innerText();
 await page.reload();await page.locator('#audioFileInput').setInputFiles({name:'empty.wav',mimeType:'audio/wav',buffer:Buffer.alloc(0)});await page.locator('#screenFailed').waitFor({state:'visible'});proof.empty=await page.locator('#failedReasonText').innerText();
 // Return a genuine empty musical result: controls still work and no stale piano state.
 await page.reload();await page.route('**/api/analyze',r=>r.fulfill({json:{...data,chord_progression:[],melody_notes:[]}}));await page.locator('#audioFileInput').setInputFiles('fixture_pop_C.wav');await page.locator('#screenWorkspace').waitFor({state:'visible'});assert.equal(await page.locator('.active-chord,.active-melody').count(),0);assert.equal(await page.locator('#currentNote').innerText(),'Rest');proof.emptyEvents=true;await page.unroute('**/api/analyze');
 // Delayed reply after cancel must never reopen the workspace.
 await page.click('#btnNewSong');await page.route('**/api/analyze',async r=>{await new Promise(resolve=>setTimeout(resolve,1500));await r.fulfill({json:data}).catch(()=>{});});await page.locator('#audioFileInput').setInputFiles('fixture_pop_C.wav');await page.locator('#screenAnalyzing').waitFor({state:'visible'});await page.click('#btnCancel');await page.waitForTimeout(1800);assert(await page.locator('#screenImport').isVisible());proof.cancel=true;await page.unroute('**/api/analyze');
 // Sample button fetches real packaged audio and reaches live inference.
 await page.click('#btnSample');await page.locator('#screenWorkspace').waitFor({state:'visible',timeout:180000});proof.sample=true;
 fs.writeFileSync('evidence/edge-proof.json',JSON.stringify(proof,null,2));console.log(proof);await browser.close();assert(proof.landing320.scroll<=320);assert(proof.workspace320.scroll<=320);
})().catch(e=>{console.error(e);process.exit(1)});
