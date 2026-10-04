# FASTKEYS

Hear a song, follow its chords and tonic solfa, and find the notes on your keyboard.

[Production](https://fastkeys.onrender.com) · [Current verification](evidence/README.md) · [Director handoff](director.md)

You have a song to play and little time to learn it. FASTKEYS gives keyboardists a live musical guide: upload a recording, press Play, then follow the current degree, chord, melody and piano as the actual recording moves.

The rebuilt interface uses one full-viewport musical environment from import through Play-Along. The landing keeps the full-bleed hero above the fold, then unfolds into a scroll narrative: the musician problem, four editorial outputs, an illustrated moving Play-Along map, three steps, a song-to-keys transformation diagram, and a final upload CTA. Playback, seeking and transposition all render from the same audio timestamp.

The landing story uses inline SVG for the staff-to-degree artwork, step connectors and transformation map. Reveals are native `IntersectionObserver` transitions with a requestAnimationFrame-throttled parallax offset; reduced-motion preferences remove the movement and path drawing. The compact layout was checked at 390px without horizontal overflow. The Play-Along screens and API contract remain unchanged.

## Run locally

Python 3.11 and FFmpeg on PATH are required. The production container installs FFmpeg. No frontend build or JavaScript framework is needed.

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
.\.venv311\Scripts\python.exe server.py
```

Open http://127.0.0.1:8000 and choose a song, or select **Try a sample**. The sample is packaged audio and goes through the real analysis API. It needs no account or API key.

For the same Linux runtime used by Render:

```sh
docker build -t fastkeys .
docker run --rm -p 8000:10000 fastkeys
```

The Windows runtime and existing virtual environment were exercised for this rebuild. The Docker recipe was inspected; a new container build was not part of the verified run.

## How it works

1. Upload a recording. The browser keeps a temporary local blob for playback.
2. FastAPI decodes the complete upload. DSP estimates the key and triads across the full waveform; Spotify Basic Pitch analyzes short overlapping chunks and maps every note back to the original song timeline.
3. The browser interprets timestamps and key-relative notation, then opens directly into Play-Along.
4. Native audio playback supplies the clock. Chord, degree, melody and piano follow `audio.currentTime`; seeking recomputes all of them.
5. Transpose shifts guide chord names, sounding-note labels and piano pitches together. Relative degrees and unambiguous solfa remain unchanged.

| File | Job |
|---|---|
| `server.py` | Serve audio analysis and clean up temporary uploads |
| `engine.py` | Detect key, chords and melody using DSP and Basic Pitch |
| `web/index.html` / `web/style.css` | Present import and live musical workspace |
| `web/music.js` | Spell pitches, degrees and contextual movable-do solfa |
| `web/app.js` | Drive playback, seeking, uploads and synchronized rendering |

Landing evidence is in [`evidence/landing-story-desktop-full.png`](evidence/landing-story-desktop-full.png), [`evidence/landing-story-mobile-full.png`](evidence/landing-story-mobile-full.png), and the sequential section captures beside them. The machine-readable proof is [`evidence/landing-story-proof.json`](evidence/landing-story-proof.json); it records zero horizontal overflow, 16/16 reveals after the scroll pass, four inline SVGs and zero browser errors.

## Verification

```powershell
node --test test_music.cjs
.\.venv311\Scripts\python.exe -m unittest test_long_song_engine -v
.\.venv311\Scripts\python.exe -m unittest test_production_smoke -v
```

The pure JavaScript regression needs only Node. The smoke suite additionally uses `requests` and a running server. Browser tests need an installed `playwright-core` and Chromium; set `FASTKEYS_PLAYWRIGHT_MODULE` and `FASTKEYS_BROWSER` to their paths when they differ from the author's machine. `test_minor_browser.cjs` uses a credited Chopin E-minor piano recording for the accepted real minor-key proof; the source file and checked-in analysis/evidence document the tested input.

```powershell
node test_browser.cjs
node test_browser_edges.cjs
node test_minor_browser.cjs
node test_long_song_browser.cjs
```

The exact +2 invariant is tested at both pure-logic and DOM/piano levels: `C | F | G | Am` becomes `D | G | A | Bm`; degrees stay `1 | 4 | 5 | 6m`; `l (A)` becomes `l (B)` with piano MIDI 69 becoming 71.

Tests include backward/forward seeks, rests and event boundaries, destination-key spelling, minor-key solfa, empty files, unsupported files, failed analysis, empty results, cancellation, original blob playback, decoded nonzero audio samples, narrow mobile layouts, full-duration chord coverage, absolute chunk timestamps, overlap deduplication and a real 188-second song at 5/25/50/75/95 percent plus final-state and random-seek checks. See the evidence index for actual results and limitations. The long-song browser script can use another server with `FASTKEYS_SERVER_URL` when required.

The landing-only browser capture helper is `capture_landing_story.cjs`. It creates desktop/mobile long-page screenshots plus one viewport capture for the hero, problem, outputs, preview, steps, transformation and final CTA. Leave the worktree uncommitted until the owner completes visual UAT; the current local rebuild is not claimed as deployed to the public Render URL.

## Honest limits

- Guidance covers the complete decoded upload. Long recordings use sequential 30-second Basic Pitch chunks with 3 seconds of overlap; the uploaded recording still plays in full and every returned event uses absolute song timestamps.
- The accepted local long-song run used `st_louis_blues.mp3` at 188.151 seconds: seven chunks, 103.463 seconds total analysis, 75.528 seconds Basic Pitch, 27.64 seconds DSP and 621.2 MB in-process peak in the notation rerun. The final chord reaches the measured duration while the final melody rest remains neutral. This proves the local path; it does not prove a live Render deployment of the rebuilt code.
- Transpose changes the keyboard guide. It does **not** pitch-shift the recording; the player explicitly says so.
- Key and melody detection are estimates. Clear piano or melody-forward recordings work better than dense choirs, orchestral mixes or heavily distorted audio. The existing Für Elise recording remains a retained key-detection limitation in the evidence.
- Solfa uses movable-do / do-based minor. Ambiguous chromatic direction displays a note name instead of two competing syllables.
- Piano melody pitches are folded into two visible octaves. Pitch class is preserved, but the displayed octave can differ from the source.
- Uploads use server temporary files and are deleted after analysis. The browser blob is released on New Song. Cancelling stops the client from waiting; already running server inference finishes and performs its cleanup.
- This phase stops for owner visual UAT. Production state and the local Git state are recorded in `director.md`; a healthy production URL alone does not prove that the rebuild is deployed.

Spotify Basic Pitch is an Apache-2.0 dependency. No separate license for the FASTKEYS application or ownership claim for the user-supplied artwork is asserted here.
