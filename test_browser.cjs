// Run with FASTKEYS_PLAYWRIGHT_MODULE pointing at an installed playwright-core.
const {chromium}=require(process.env.FASTKEYS_PLAYWRIGHT_MODULE||'playwright-core');
const fs=require('node:fs'),assert=require('node:assert/strict');
const base=process.env.FASTKEYS_SERVER_URL||'http://127.0.0.1:8000';
const executablePath=process.env.FASTKEYS_BROWSER;
const snap=page=>page.evaluate(()=>({time:document.querySelector('audio').currentTime,paused:document.querySelector('audio').paused,src:document.querySelector('audio').src,ready:document.querySelector('audio').readyState,degree:document.querySelector('#currentDegree').textContent,chord:document.querySelector('#currentChord').textContent,solfa:document.querySelector('#currentSolfa').textContent,note:document.querySelector('#currentNote').textContent,chordKeys:[...document.querySelectorAll('.active-chord')].map(e=>+e.dataset.midi),melodyKeys:[...document.querySelectorAll('.active-melody')].map(e=>+e.dataset.midi),activeChord:document.querySelector('.chord-item.active')?.id,activeSolfa:document.querySelector('.solfa-item.active')?.id}));
(async()=>{
 fs.mkdirSync('evidence',{recursive:true});const browser=await chromium.launch({headless:true,executablePath});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const evidence={};
 await page.goto(base);await page.screenshot({path:'evidence/landing-desktop.png',fullPage:true});
 evidence.fullBleed=await page.locator('.environment').evaluate(e=>({rect:e.getBoundingClientRect().toJSON(),background:getComputedStyle(e).backgroundImage,size:getComputedStyle(e).backgroundSize,position:getComputedStyle(e).position,viewport:[innerWidth,innerHeight]}));
 assert.equal(evidence.fullBleed.rect.width,1440);assert.equal(evidence.fullBleed.rect.height,1000);assert.equal(evidence.fullBleed.size,'cover');
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'evidence/landing-mobile.png',fullPage:true});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.setViewportSize({width:1440,height:1000});
 // Fresh real upload, with the actual inference response retained as evidence.
 const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/analyze')&&r.request().method()==='POST',{timeout:180000});
 await page.locator('#audioFileInput').setInputFiles('fixture_pop_C.wav');await page.locator('#screenAnalyzing').waitFor({state:'visible'});await page.screenshot({path:'evidence/analyzing-desktop.png'});
 const response=await responsePromise;assert.equal(response.status(),200);const data=await response.json();fs.writeFileSync('evidence/pop-analysis.json',JSON.stringify(data,null,2));
 await page.locator('#screenWorkspace').waitFor({state:'visible'});await page.screenshot({path:'evidence/playalong-desktop.png',fullPage:true});evidence.before=await snap(page);
 await page.click('#btnPlayPause');await page.waitForTimeout(1100);evidence.play1=await snap(page);await page.waitForTimeout(2700);evidence.play2=await snap(page);
 assert(evidence.play2.time>evidence.play1.time+2);assert(!evidence.play2.paused);assert(evidence.play2.src.startsWith('blob:'));assert(evidence.play2.ready>=2);
 await page.screenshot({path:'evidence/playalong-playing.png',fullPage:true});await page.click('#btnPlayPause');
 for(const t of [1,3,6,1]){
  await page.locator('#timelineTrack').fill(String(t));await page.locator('#timelineTrack').dispatchEvent('input');await page.waitForTimeout(100);
  const state=await snap(page);const expected=require('./web/music.js').moment(data,t);assert.equal(state.degree,expected.chord?.degree||'·');assert.equal(state.note,expected.melody?.note||'Rest');evidence['seek'+t]=state;
 }
 await page.click('#chord-item-1');await page.waitForTimeout(100);assert(Math.abs((await snap(page)).time-data.chord_progression[1].start)<.1);
 await page.click('#solfa-item-2');await page.waitForTimeout(100);assert(Math.abs((await snap(page)).time-data.melody_notes[2].start)<.1);
 await page.click('#btnRestart');assert((await snap(page)).time<.1);await page.click('#btnSeekForward');assert(Math.abs((await snap(page)).time-5)<.1);await page.click('#btnSeekBack');assert((await snap(page)).time<.1);
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'evidence/playalong-mobile.png',fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.click('#btnNewSong');assert(await page.locator('#screenImport').isVisible());assert.equal(await page.locator('audio').getAttribute('src'),null);
 // Explicit deterministic UI regression fixture, separate from the real inference run.
 const fixture={filename:'Transpose regression.wav',duration:8,key:'C Major',chord_progression:['C','F','G','Am'].map((chord,i)=>({chord,start:i*2,end:(i+1)*2})),melody_notes:[{midi:69,start:0,end:8}]};
 await page.route('**/api/analyze',route=>route.fulfill({json:fixture}));await page.setViewportSize({width:1440,height:1000});await page.locator('#audioFileInput').setInputFiles('fixture_pop_C.wav');await page.locator('#screenWorkspace').waitFor({state:'visible'});
 evidence.transposeBefore=await snap(page);await page.click('#btnTransposeUp');await page.click('#btnTransposeUp');evidence.transposeAfter=await snap(page);
 assert.equal(evidence.transposeBefore.solfa,'l');assert.equal(evidence.transposeBefore.note,'A');assert.equal(evidence.transposeAfter.solfa,'l');assert.equal(evidence.transposeAfter.note,'B');assert.deepEqual(evidence.transposeAfter.melodyKeys,[71]);
 assert.deepEqual(await page.locator('.chord-item-name').allTextContents(),['D','G','A','Bm']);assert.deepEqual(await page.locator('.chord-item-degree').allTextContents(),['1','4','5','6m']);
 await page.screenshot({path:'evidence/transpose-plus2.png',fullPage:true});await page.unroute('**/api/analyze');
 // Real minor recording is uploaded anew through the browser, without mocked analysis.
 await page.click('#btnNewSong');const minorResponse=page.waitForResponse(r=>r.url().endsWith('/api/analyze'),{timeout:180000});await page.locator('#audioFileInput').setInputFiles('fur_elise.ogg');const mr=await minorResponse;assert.equal(mr.status(),200);const minor=await mr.json();fs.writeFileSync('evidence/minor-browser-analysis.json',JSON.stringify(minor,null,2));await page.locator('#screenWorkspace').waitFor({state:'visible'});
 evidence.minor={key:minor.key,chords:await page.locator('.chord-item-name').allTextContents(),solfa:[...new Set(await page.locator('.solfa-item-syllable').allTextContents())]};
 await page.click('#btnPlayPause');await page.waitForTimeout(3000);evidence.minor.playing=await snap(page);await page.screenshot({path:'evidence/minor-playalong.png',fullPage:true});await page.click('#btnPlayPause');
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'evidence/minor-mobile.png',fullPage:true});
 evidence.errors=errors;fs.writeFileSync('evidence/browser-proof.json',JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence,null,2));assert.deepEqual(errors,[]);assert(/Minor/i.test(minor.key),'Real recording must detect a minor key');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
