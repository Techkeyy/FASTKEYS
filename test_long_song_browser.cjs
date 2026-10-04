const { chromium } = require('C:/Users/HomePC/Desktop/CLINCH-DEMO/node_modules/playwright-core');
const fs = require('fs');
const assert = require('node:assert/strict');

const base = process.env.FASTKEYS_SERVER_URL || 'http://127.0.0.1:8012';
const source = 'st_louis_blues.mp3';
const executablePath = 'C:/Users/HomePC/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe';

function activeEvent(events, t, duration, includeFinal = false) {
  const last = events.length - 1;
  return events.find((event, index) => t >= event.start && (t < event.end || (includeFinal && index === last && t <= duration))) || null;
}

async function seekAndRead(page, data, fraction) {
  const target = data.duration * fraction;
  await page.evaluate(async (time) => {
    const audio = document.querySelector('audio');
    audio.pause();
    audio.currentTime = time;
    await new Promise(resolve => {
      const done = () => resolve();
      audio.addEventListener('seeked', done, { once: true });
      setTimeout(done, 800);
    });
    audio.dispatchEvent(new Event('seeking'));
  }, target);
  await page.waitForTimeout(120);
  const state = await page.evaluate(() => ({
    time: document.querySelector('audio').currentTime,
    paused: document.querySelector('audio').paused,
    degree: document.querySelector('#currentDegree').textContent,
    chord: document.querySelector('#currentChord').textContent,
    solfa: document.querySelector('#currentSolfa').textContent,
    note: document.querySelector('#currentNote').textContent,
    chordIndex: [...document.querySelectorAll('#chordStream button')].findIndex(button => button.classList.contains('active')),
    melodyIndex: [...document.querySelectorAll('#solfaStream button')].findIndex(button => button.classList.contains('active')),
    chordKeys: [...document.querySelectorAll('.active-chord')].map(key => Number(key.dataset.midi)),
    melodyKeys: [...document.querySelectorAll('.active-melody')].map(key => Number(key.dataset.midi)),
    timeline: Number(document.querySelector('#timelineTrack').value),
  }));
  const chordEvent = activeEvent(data.chord_progression, state.time, data.duration, true);
  const melodyEvent = activeEvent(data.melody_notes, state.time, data.duration, false);
  return {
    fraction,
    target,
    audioTime: state.time,
    displayed: state,
    backend: {
      chordIndex: chordEvent ? data.chord_progression.indexOf(chordEvent) : -1,
      chordStart: chordEvent?.start ?? null,
      chordEnd: chordEvent?.end ?? null,
      melodyIndex: melodyEvent ? data.melody_notes.indexOf(melodyEvent) : -1,
      melodyStart: melodyEvent?.start ?? null,
      melodyEnd: melodyEvent?.end ?? null,
    },
    chordCovered: !!chordEvent,
    melodyIsRest: !melodyEvent,
  };
}

;(async () => {
  fs.mkdirSync('evidence', { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  await page.goto(base, { waitUntil: 'networkidle' });
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/analyze') && response.request().method() === 'POST', { timeout: 300000 });
  await page.locator('#audioFileInput').setInputFiles(source);
  await page.locator('#screenWorkspace').waitFor({ state: 'visible', timeout: 300000 });
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  const data = await response.json();
  await page.waitForFunction(() => document.querySelector('audio').readyState >= 1 && document.querySelector('audio').duration > 0);
  const points = [];
  for (const fraction of [0.05, 0.25, 0.50, 0.75, 0.95]) points.push(await seekAndRead(page, data, fraction));
  const finalStates = [];
  for (const fraction of [Math.max(0, (data.duration - 10) / data.duration), Math.max(0, (data.duration - 5) / data.duration), Math.max(0, (data.duration - 1) / data.duration)]) finalStates.push(await seekAndRead(page, data, fraction));
  await page.screenshot({ path: 'evidence/long-song-final-10s.png', fullPage: true });
  const seeks = [];
  for (const fraction of [0.10, 0.80, 0.35, 0.95]) seeks.push(await seekAndRead(page, data, fraction));
  await page.evaluate(() => { document.querySelector('audio').currentTime = 0; });
  await page.click('#btnPlayPause');
  await page.waitForTimeout(1200);
  const playback = await page.evaluate(() => ({ time: document.querySelector('audio').currentTime, paused: document.querySelector('audio').paused, degree: document.querySelector('#currentDegree').textContent, chord: document.querySelector('#currentChord').textContent }));
  await page.click('#btnPlayPause');
  for (const sample of [...points, ...finalStates]) {
    assert.equal(sample.displayed.chordIndex, sample.backend.chordIndex, `chord index drift at ${sample.fraction}`);
    assert.equal(sample.displayed.melodyIndex, sample.backend.melodyIndex, `melody index drift at ${sample.fraction}`);
    assert(sample.chordCovered, `missing chord coverage at ${sample.fraction}`);
    assert(Math.abs(sample.displayed.timeline - sample.audioTime) < 0.1, `timeline drift at ${sample.fraction}`);
  }
  for (const sample of seeks) {
    assert.equal(sample.displayed.chordIndex, sample.backend.chordIndex, `seek chord drift at ${sample.fraction}`);
    assert.equal(sample.displayed.melodyIndex, sample.backend.melodyIndex, `seek melody drift at ${sample.fraction}`);
    assert(sample.chordCovered, `seek missing chord at ${sample.fraction}`);
  }
  assert(playback.time > 0.7 && !playback.paused, 'audio did not advance during Play');
  assert.deepEqual(errors, []);
  const report = {
    source,
    base,
    duration: data.duration,
    analysisChunks: data.analysis_chunks,
    chunkSeconds: data.analysis_chunk_seconds,
    overlapSeconds: data.analysis_overlap_seconds,
    basicPitchSeconds: data.basic_pitch_seconds,
    dspSeconds: data.dsp_seconds,
    analysisSeconds: data.analysis_seconds,
    peakMemoryMb: data.peak_memory_mb,
    finalEventCounts: { chords: data.chord_progression.length, melody: data.melody_notes.length, rawNotes: data.raw_note_count },
    points,
    finalStates,
    seeks,
    playback,
    errors,
  };
  fs.writeFileSync('evidence/long-song-browser-proof.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
