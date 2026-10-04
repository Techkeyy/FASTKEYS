const { chromium } = require('C:/Users/HomePC/Desktop/CLINCH-DEMO/node_modules/playwright-core');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const base = process.env.FASTKEYS_SERVER_URL || 'http://127.0.0.1:8012';
const source = 'timing_fixture_C.wav';
const executablePath = process.env.FASTKEYS_BROWSER || 'C:/Users/HomePC/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe';
const expectedMelody = [
  { midi: 60, start: 0.25, end: 0.75 },
  { midi: 65, start: 1.25, end: 1.75 },
  { midi: 67, start: 2.25, end: 2.75 },
  { midi: 64, start: 3.25, end: 3.75 },
];
const expectedChordStarts = [0, 1, 2, 3];

function nearestEvent(events, expected, field) {
  return events.reduce((best, event, index) => {
    const error = Math.abs(event[field] - expected);
    return !best || error < best.error ? { event, index, error } : best;
  }, null);
}

function firstTraceAt(trace, field, index, start) {
  return trace.find(entry => entry[field] === index && entry.audioTime + 1e-4 >= start) || null;
}

;(async () => {
  fs.mkdirSync('evidence', { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.addInitScript(() => {
    window.__FASTKEYS_TIMING_TRACE__ = true;
    window.__fastkeysTimingTrace = [];
  });
  const errors = [];
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });

  await page.goto(base, { waitUntil: 'networkidle' });
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/analyze') && response.request().method() === 'POST', { timeout: 300000 });
  await page.locator('#audioFileInput').setInputFiles(source);
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  const data = await response.json();
  await page.locator('#screenWorkspace').waitFor({ state: 'visible', timeout: 300000 });
  await page.waitForFunction(() => document.querySelector('audio').readyState >= 1 && document.querySelector('audio').duration > 0);

  const backendMelody = expectedMelody.map(expected => nearestEvent(data.melody_notes, expected.start, 'start'));
  for (const match of backendMelody) assert(match && match.error < 0.15, `backend melody start drift: ${match?.error}`);
  const backendChords = expectedChordStarts.map(start => nearestEvent(data.chord_progression, start, 'start'));
  for (const match of backendChords) assert(match && match.error < 0.15, `backend chord start drift: ${match?.error}`);

  await page.evaluate(() => {
    const audio = document.querySelector('audio');
    audio.currentTime = 0;
    audio.dispatchEvent(new Event('seeking'));
  });
  await page.click('#btnPlayPause');
  await page.waitForTimeout(4800);
  await page.click('#btnPlayPause');
  const trace = await page.evaluate(() => window.__fastkeysTimingTrace || []);
  assert(trace.length > 8, `expected timing trace entries, got ${trace.length}`);

  const melodyTransitions = backendMelody.map((match, index) => {
    const entry = firstTraceAt(trace, 'melodyIndex', match.index, match.event.start);
    assert(entry, `missing browser melody transition ${index}`);
    return { index, backend: match.event, entry, latencyMs: (entry.audioTime - match.event.start) * 1000 };
  });
  const chordTransitions = backendChords.map((match, index) => {
    const entry = firstTraceAt(trace, 'chordIndex', match.index, match.event.start);
    assert(entry, `missing browser chord transition ${index}`);
    return { index, backend: match.event, entry, latencyMs: (entry.audioTime - match.event.start) * 1000 };
  });
  for (const transition of [...melodyTransitions, ...chordTransitions]) {
    assert(transition.latencyMs >= -2, `rendered before backend event at ${transition.index}`);
    assert(transition.latencyMs < 250, `browser render latency exceeded 250ms at ${transition.index}: ${transition.latencyMs}`);
  }

  const invariantChecks = [];
  for (const entry of trace) {
    const expected = await page.evaluate(({ entry, notes, key }) => {
      const M = window.FastkeysMusic;
      if (entry.melodyIndex < 0) return { solfa: '·', note: 'Rest', midi: null };
      const value = M.melody(notes, entry.melodyIndex, key);
      let midi = value.midi;
      if (midi != null) { while (midi < 48) midi += 12; while (midi > 72) midi -= 12; }
      return { solfa: value.solfa, note: value.note, midi };
    }, { entry, notes: data.melody_notes, key: data.key });
    assert.equal(entry.displayedSolfa, expected.solfa, `solfa mismatch at ${entry.audioTime}`);
    assert.equal(entry.displayedNote, expected.note, `note mismatch at ${entry.audioTime}`);
    assert.deepEqual(entry.highlightedPianoMidi, expected.midi == null ? [] : [expected.midi], `melody piano mismatch at ${entry.audioTime}`);
    invariantChecks.push({ audioTime: entry.audioTime, melodyIndex: entry.melodyIndex, passed: true });
  }

  await page.evaluate(() => {
    const audio = document.querySelector('audio');
    audio.pause();
    audio.currentTime = 0.9;
    audio.dispatchEvent(new Event('seeking'));
  });
  await page.waitForTimeout(120);
  const restState = await page.evaluate(() => ({
    time: document.querySelector('audio').currentTime,
    solfa: document.querySelector('#currentSolfa').textContent,
    note: document.querySelector('#currentNote').textContent,
    melodyKeys: [...document.querySelectorAll('.active-melody')].map(key => Number(key.dataset.midi)),
    chordKeys: [...document.querySelectorAll('.active-chord')].map(key => Number(key.dataset.midi)),
  }));
  assert(restState.solfa === '·' && restState.note === 'Rest', 'rest state did not clear melody display');
  assert.deepEqual(restState.melodyKeys, [], 'rest state retained a melody piano highlight');
  assert(restState.chordKeys.length > 0, 'rest state lost independent chord tones');

  const latencyMs = melodyTransitions.concat(chordTransitions).map(item => item.latencyMs);
  const report = {
    source,
    base,
    duration: data.duration,
    backend: {
      key: data.key,
      chords: data.chord_progression,
      melody: data.melody_notes,
      expectedMelody,
      expectedChordStarts,
    },
    traceEntries: trace.length,
    melodyTransitions,
    chordTransitions,
    renderLatencyMs: { mean: latencyMs.reduce((sum, value) => sum + value, 0) / latencyMs.length, max: Math.max(...latencyMs) },
    invariantChecks,
    restState,
    errors,
  };
  fs.writeFileSync('evidence/timing-gate-browser-proof.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  assert.deepEqual(errors, []);
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
