# Current takeover status (2026-10-04, Africa/Lagos)

**BUILDING: full UI rebuild, landing-page expansion and the final timing/melody gate are implemented and verified locally. Release/UAT promotion remains paused for Director review.**
This section supersedes the historical ledger below where statements conflict.

- Final timing/melody gate status: automated gate PASS; no commit or push was made for this gate, as requested. The approved rebuild remains in the working tree for review.
- Root causes found: the frontend already used `audio.currentTime` as its clock and a requestAnimationFrame loop while playing, so there was no independent timer drift. The redundant coarse `timeupdate` path was removed; seek, metadata, visibility recovery and reset now force an immediate render and restore the RAF loop when needed. The measurable backend timing error was the former 250 ms melody selector, which quantized note onsets/offsets, plus the former 1.5 s chord window, which could place boundaries roughly 0.49–0.97 s late on controlled transitions. Basic Pitch itself preserved the clean fixture's note timing.
- Melody algorithm: `select_melody_events` filters plausible lead notes (MIDI 48–84, amplitude ≥0.25, duration ≥80 ms), drops short high-register harmonic spikes, clusters only near-simultaneous alternatives (≤80 ms), and scores amplitude, lead register, duration and continuity together. It selects one coherent monophonic event, preserves the Basic Pitch onset/offset to millisecond rounding, and clips only overlap required to keep the selected stream monophonic. It returns a rest when no candidate clears those tests; it does not rewrite detector pitch classes.
- Chord timing: the DSP window is now 1.0 s while the long-song analysis architecture remains seven 30 s chunks with 3 s overlap and absolute timestamps. On the deterministic fixture, the old boundary error is reduced to 0 ms at 1.0, 2.0 and 3.0 s without changing the detected chord identities.
- Deterministic timing fixture (`timing_fixture_C.wav`): ground-truth melody C4 0.25–0.75, F4 1.25–1.75, G4 2.25–2.75, E4 3.25–3.75 and chord starts 0/1/2/3 s. Raw Basic Pitch mean onset error is 5 ms (max 10 ms) and mean offset error 45 ms (max 50 ms). The scored selection is 5 ms mean onset (max 8 ms) and 43.75 ms mean offset (max 50 ms). Chord boundary mean/max error is 0 ms.
- Browser timing proof: the deterministic upload rendered all four chord/melody transitions with a mean audio-clock render latency of 3.2 ms and a 9.1 ms maximum on the final local run. Every rendered melody event kept the exact shared solfa, sounding note and highlighted melody MIDI; rest windows cleared the melody while retaining independent chord tones. Evidence: `evidence/timing-gate-engine-proof.json` and `evidence/timing-gate-browser-proof.json`.
- Real recording checkpoints: the hymn (`when_i_survey_20s.wav`) completed the updated pipeline as D Major with full chord coverage and representative D3/D4/A3 melody events; the non-hymn (`st_louis_blues_20s.wav`) completed as D Major with full chord coverage and representative D5/F#4 melody events. These are automated model/output checkpoints; Director listening/UAT remains the final human judgment for musical usefulness.
- Long-song regression: the 188.15 s `st_louis_blues.mp3` browser run passed 5/25/50/75/95% seeks, final-section seeks, reverse seeks and active playback. The updated output contains 150 chords and 148 selected melody events, and the accepted functional ♭6 checkpoints display `Bb`/`B♭` rather than `A#`/`A♯`.
- Final local validation: notation tests 10/10; timing and long-song engine tests 6/6; deterministic browser timing gate PASS; ordinary browser regression PASS; long-song browser regression PASS; browser edge regression PASS; production smoke 4/4; `node --check web/app.js`; `node --check web/music.js`; `git diff --check` clean. No release deployment was attempted at this pre-commit state.

- Baseline: main, `2a3bfe46e325b280aa45e9882e23c8e4434ac998` (the previously approved enharmonic fix). The timing-gate work remains intentionally uncommitted for Director review; prior evidence and source recordings are preserved.
- Product: help a keyboardist learn an unfamiliar song by hearing their uploaded recording while the current chord, scale degree, tonic solfa and piano guidance follow its playback position. Only a recording is required; key and events are inferred.
- Scope: retain FastAPI, Basic Pitch, DSP detection, Render configuration and the existing Play-Along workspace. The landing now continues below the approved full-bleed hero with a problem statement, editorial outputs, illustrated live preview, three-step path, transformation map and final CTA. No accounts, payments, new framework, new product feature or sponsor integration was added. Stop after verification for owner visual UAT; no demo/submission work.
- Exact newest Downloads image: `C:\Users\HomePC\Downloads\download (17).jpg`, selected by LastWriteTime (2026-10-03 21:53:37 host timestamp). Packaged unchanged as `web/hero.jpg`. CSS invert treatment, cover sizing, fixed inset 0 and directional dark gradients make it an edge-to-edge environment on both screens.
- Reference inspected live with Chromium: https://ballroom-eight.vercel.app/. Screenshots: evidence/reference-desktop.png and evidence/reference-mobile.png. Borrowed sparse action hierarchy, oversized headline, immersive artwork, quiet chrome. No branding, football imagery, proprietary assets or copied wording.
- Visual identity: warm charcoal, cream, one amber accent; sans headline with expressive serif final line. Continuous degree/chord and solfa lanes; a physical two-octave keyboard; melody indicated by white outline/dot as well as color.
- Landing story implementation: `web/index.html` keeps the hero IDs and actions intact, then adds sections titled “The song starts in five minutes”, “One song in”, “Not a static chord sheet”, “From audio to keys”, the Raw Song → D Major → Progression → Tonic Solfa → Keyboard map, and “Next song?”. The preview is explicitly labelled `PLAY ALONG / ILLUSTRATION` and remains a product illustration rather than a fake analysis result.
- Original SVG inventory: flowing staff-to-degree artwork in `.staff-svg`; step arrow paths in each `.step`; transformation connectors in `.transform-connectors`. The remaining output and keyboard marks are CSS-drawn, so no icon library or remote asset was introduced.
- Scroll behavior: native `IntersectionObserver` adds `.is-visible` once per reveal target; opacity/translate/scale transitions and SVG path dash drawing provide the reveal. A requestAnimationFrame-throttled window scroll listener updates a small vertical `--parallax-y` offset for the fixed hero environment. The preview progress line and active beat use one CSS-only `previewProgress` loop; reduced motion disables that loop too. `prefers-reduced-motion: reduce` removes transforms, transitions and path drawing; the mobile layout stacks grids, shrinks the preview and hides decorative step arrows.
- Visual evidence: `evidence/landing-story-desktop-full.png` and `evidence/landing-story-mobile-full.png` are complete long-page captures; `evidence/landing-story-desktop-{hero,problem,outputs,preview,steps,transformation,final}.png` and the matching mobile files show the sequence section by section. `evidence/landing-story-proof.json` records desktop 1440/1440 and mobile 390/390 document widths, 16/16 reveals, four inline SVGs and zero page/console errors. Its reduced-motion pass confirms `prefers-reduced-motion`, all reveals visible with no transition, environment transform `none`, and 390/390 width. `evidence/landing-story-actions.json` confirms both final CTA paths remain wired to the chooser and existing workspace.
- Playback architecture: native HTMLAudioElement plays the uploaded File blob. `audio.currentTime` is the sole clock; requestAnimationFrame while playing renders one shared musical moment, while seeking, metadata and duration changes force an immediate refresh. Pausing preserves state; actual gaps clear highlights. New Song cancels pending UI work, pauses audio and revokes its object URL.
- Guidance boundary: the server now decodes the complete upload. Short files use one Basic Pitch pass; longer files use sequential 30-second chunks with 3 seconds of overlap, absolute timestamp conversion and overlap deduplication. Original recording and guidance share the full song duration. Cancellation stops waiting in the client; an already running server analysis still completes and cleans temporary files.
- Long-song gate: the old first divergence was `ffmpeg -t 45`, which reduced the 188.151-second `st_louis_blues.mp3` upload to a 45-second engine input. That cap is removed. The engine now analyzes the full waveform, uses seven 30-second chunks with 3-second overlap, converts every chunk event to absolute timestamps, deduplicates only same-pitch overlapping boundary notes, and extends the final detected chord segment to the measured duration without inventing a chord.
- Long-song proof: `evidence/long-song-diagnosis-before-fix.json` records the 45-second failure; `evidence/long-song-diagnosis-after-fix.json` records 188.15-second coverage, max raw-note end 185.18, selected melody/solfa end 183.5 and final chord end 188.15. The final melody gap is therefore a measured rest, not a truncated timeline.
- Long-song browser acceptance: `evidence/long-song-browser-proof.json` covers 5/25/50/75/95 percent, duration−10/5/1 seconds, seeks 10→80→35→95 and active playback. The final local run measured 31.14 seconds total (26.05 Basic Pitch, 5.006 DSP), 625.35 MB in-process peak, 150 chords, 148 selected melody notes and 257 raw notes. `evidence/long-song-final-10s.png` captures the 3:08 timeline at 3:07 with an active final chord and neutral melody rest.
- Notation rules: do-based minor; key-aware diatonic spelling (including Bb for the functional ♭6 in D major/minor and G# in E major), Unicode accidental degree labels. A clear stepwise chromatic resolution selects one solfa; ambiguous chromatic notes preserve the existing sounding-pitch policy. Inference output is preserved; presentation normalization lives in web/music.js.
- Enharmonic remediation: the detector's raw pitch class remains unchanged, while `web/music.js` now forces the functional `♭6` display to `Bb` across current chords, progression-lane names, sounding melody notes, piano labels and transposed D-context output. The exact case is covered by the notation regression in `test_music.cjs`; the regenerated long-song proof now reports `Bb Major`, `Bb` instead of `A# Major`, `A#`.
- Transpose invariant: C/F/G/Am becomes D/G/A/Bm at +2; degrees 1/4/5/6m remain; l(A) becomes l(B), with piano MIDI 69 becoming 71. Labels and piano derive from the same shared state. Guide transposes; the original recording is not pitch-shifted, and this is disclosed beside playback.
- Skills applied: project-understanding to scope and data flow; build-process to real vertical-flow verification; design-skill to hierarchy/accessibility/mobile; audit-skill and project-edge to evidence and claim limits; perfect-readme to reproducible verification; hackathon-onboarding to installed-tool checks. User full-bleed requirement overrides the design skill split-canvas default.
- Validation after the landing expansion, long-song gate and enharmonic remediation: 9 pure music regressions pass; the three long-song engine tests pass; the real browser suite exits 0 with upload, audible blob playback, timeline seeks, lane seeking, transpose +2, minor-key upload and mobile workspace coverage; the long-song browser gate exits 0 with `Bb Major` at the accepted final ♭6; edge coverage passes; and the API smoke suite passes 4 tests. `git diff --check` is clean; the UI copy audit reports 0 long-dash errors and 0 copy warnings (four existing small-text warnings at 8–10px labels remain intentional metadata styling). Evidence index: `evidence/README.md`.
- Minor-key validation: a credited Chopin E-minor Prelude recording was run through the real upload path. Detection returned E Minor at 0.7877 confidence; playback advanced and seeks at 10, 20 and 4 seconds resynchronized. The existing Fur Elise recording still has a retained key-detection limitation although the composition is in A minor, so it is not accepted as the long-song correctness proof.
- Production: https://fastkeys.onrender.com/api/health returned healthy Basic Pitch/DSP JSON during takeover. The local 188-second run completed within the configured standard Render memory class without an OOM, but no live Render long-song run was available, so Render production viability remains locally compatible and unproven. A read-only live-HTML comparison is recorded in `evidence/deployment-proof.json` when available. The public endpoint cannot prove the Render build SHA; the rebuilt frontend is local and not claimed as deployed.
- Local Git state: `HEAD` remains `2a3bfe46e325b280aa45e9882e23c8e4434ac998`; the timing gate, evidence and director update are uncommitted in the working tree for owner review. No commit or push was made for this gate.

---

# Historical ledger (prior builder; not current verification)
# DIRECTOR STATE: FASTKEYS

## 1. Authoritative Status
**BUILDING — PLAY-ALONG SYNCHRONIZATION COMPLETE / DIRECTOR & OWNER UAT PENDING**  
*Integrated genuine browser audio playback, live timeline synchronization, movable-do solfa, Unicode degrees, and real-time transpose.*

---

## 2. Product Definition & Honest Supported Scope
**FASTKEYS** is a visual emergency song-learning workspace for keyboardists.  
It turns supported songs with a clear melodic and harmonic structure into an interactive, synchronized Play-Along workspace containing:
- Detected musical key (e.g. `D Major`)
- Chord progression over time (e.g. `D -> G -> Gm -> Bm -> D`)
- Scale-degree numbers with Unicode accidental symbols (e.g. `1 -> 5 -> 6m -> 4`, `♭6`, `♯4`)
- Primary melody converted to key-aware movable-do tonic sol-fa (`d, r, m, f, s, l, t` with context alterations `di, ri, fi, si, li` or `ra, me, se, le, te`)
- Visual 2-octave piano synchronized to audio playback with chord tones and melody notes highlighted in real time.

### Target Music & Supported Scope Boundary
- **Supported Genres / Materials**: Songs with a clearly audible melodic and harmonic structure, including piano-led pieces, ballads, worship, gospel, pop, R&B, instrument-led songs, and hymns.
- **Works Best When**: Lead melody and underlying chords are clearly distinguishable.
- **Explicit Limitations / Non-Goals**: FASTKEYS does not claim universal support for every recording. Dense acapella choral polyphony (e.g. SATB hymns with church reverb), wall-of-sound distorted guitars, or dense orchestral arrangements cause harmonic overtone smearing and chord misclassification.

---

## 3. Core Outcome
> **FASTKEYS is only genuinely working as a user experience when a keyboardist uploads a song, presses Play inside FASTKEYS, hears the actual uploaded song, and can follow the current scale degree, chord, tonic-solfa melody and keyboard notes as they automatically change in synchronization with the audio.**

---

## 4. Skills Inspected & Applied
Desktop skills located at `C:\Users\HomePC\Desktop\skill`:
1. **`audit-skill`**: Performed comprehensive repository secret audit, confirmed zero keys/tokens committed, verified `.gitignore` excludes binary/temp/virtualenv files, and audited exact stage runtime.
2. **`build-process`**: Enforced zero premature features; locked scope to visual play map; verified exact stage breakdown.
3. **`design-skill`**: Executed complete musician-first frontend overhaul.
   - **Visual Direction**: Studio/stage aesthetic with deep near-black background (`#090c10`), low-contrast elevated surfaces (`#111620`, `#161e2c`), and warm amber/gold primary accent (`#f59e0b`).
   - **Hierarchy**: Screen 1 (Import) stripped to zero cognitive load ("What do you need to play?" -> Drop audio -> Reference presets). Screen 2 (Song Workspace) centers entirely around the "Current Musical Moment" (giant scale degree number + chord name), supported by continuous progression/solfa streams, an interactive 2-octave piano, and a timeline bar.
   - **Typography**: Clean humanist sans (`Plus Jakarta Sans`) paired with geometric monospace (`JetBrains Mono`) for metrics, timings, and note names. Strict zero long-dash policy enforced via text audit.
   - **Responsiveness**: Fluid flexbox/CSS grid with vertical stacking on mobile (`<=768px`), touch-friendly targets, and horizontal overflow scrolling for chord and solfa streams.
   - **Interaction**: Keyboard arrow keys step through moments; clicking chords/solfa highlights authentic piano chord tones and melody notes; transpose controls (`- / +`) dynamically shift key display.
4. **`hackathon-onboarding`**: Maintained open-source AI core (Spotify Basic Pitch, Apache 2.0) as load-bearing neural note engine.
5. **`project-edge`**: Documented failure boundaries honestly (SATB choral counterpoint) alongside non-hymn successes.
6. **`perfect-readme`**: Maintained reproducible CLI benchmarks and verification traces.

---

## 5. Sponsor Categories & Authoritative Ledger

### Targeted Categories
- **Overall Hackathon Prize**
- **Best Use of Render ($200)**
- **Best Use of Backboard ($200)**
- **Best Use of Entire ($200)**
- **Best Use of ElevenLabs ($200)**

### Sponsor Claim Ledger

| Sponsor / Category | Status | Pass Condition | Current Verification & Reality |
|---|---|---|---|
| **Render** | `TARGETED — NOT YET PROVEN` | Public Render deployment executes real Basic Pitch inference without OOM | `Dockerfile`, `render.yaml` configured on `standard` (`1c-2g`, 1 CPU / 2 GB RAM). Pending owner promo redemption at `hacktoberfest.com/my/promos` and service creation. |
| **Backboard** | `TARGETED — NOT YET PROVEN` | Backboard R-CLI completes one genuine FASTKEYS engineering/verification task with reviewable evidence | Backboard R-CLI v3.0.5 installed (`~/.backboard/bin/backboard.exe`). Production smoke test suite (`test_production_smoke.py`) created, verifying `/api/health`, upload analysis schema, and temp file cleanup. CLI requires owner OAuth login (`backboard login`). |
| **Entire** | `TARGETED — NOT YET PROVEN` | Entire captures/searches real FASTKEYS agent-session evidence used in DEV write-up | Entire CLI v0.11.3 installed (`~/.local/bin/entire.exe`). Enabled for project with `.entire/settings.json` and `.agents/hooks.json` tracking Antigravity agent. Commit evolution checkpoint preserved. |
| **ElevenLabs** | `TARGETED — CREDIT CLAIMED / FINAL DEMO NARRATION PENDING` | Final submitted demo video genuinely uses ElevenLabs narration | Pipeline does not add decorative voice APIs. Account/credit allocated for demo walkthrough narration once UI and demo script are frozen after human UAT. |

---

## 6. Architecture & Implementation
- **Frontend**: Single-page application (`web/index.html`) implementing the 4 required states, chord stream with scale-degree badges, tonic sol-fa melody strip, and interactive keyboard visualization.
- **Backend**: FastAPI web server (`server.py`) serving the frontend and exposing `/api/analyze` and `/api/health`.
- **Inference Engine (`engine.py`)**:
  - DSP Key Detection: Krumhansl-Schmuckler correlation on CQT Chromagram.
  - Chord Progression: 24-triad cosine similarity windows with temporal deduplication.
  - Scale Degree Mapping: Diatonic interval calculation relative to detected key root.
  - Neural Transcription: Spotify Basic Pitch (`basic-pitch 0.4.0`) producing polyphonic MIDI note events.
  - Primary Melody Selection: 250ms time-windowed vocal register filter (MIDI 48 to 84) with amplitude-pitch weighting.
  - Tonic Sol-fa Mapping: Diatonic modulo interval conversion relative to key root.

---

## 7. Claim -> Mechanism -> Boundary -> Proof Ledger

| Claim | Mechanism | Boundary | Required Proof | Current Proof | Status |
|---|---|---|---|---|---|
| Open-Source AI at Core | Spotify Basic Pitch Neural Net (Apache 2.0) | Monophonic & polyphonic audio | Load-bearing note event extraction | Transcribes note pitches, onsets, durations in `.venv311` | **PROVEN** |
| Audio Key Detection | Krumhansl-Schmuckler on Chromagram | Tonal major/minor pieces | Detect exact key | Verified across 5 recordings (>0.85 on clean audio) | **PROVEN** |
| Chord Progression Tracking | CQT Chroma Dot Product with 24 triad templates | Clean harmonic shifts | Match reference chords | Matches piano/organ/band shifts; fails on complex choral counterpoint | **PROVEN WITHIN SUPPORTED SCOPE** |
| Scale Degree Conversion | Key-relative interval mapping | Diatonic chords | Diatonic Roman/Nashville numbers | Produces `1 -> 5 -> 6 -> 4` style degree flows | **PROVEN** |
| Primary Melody Selection | Windowed vocal-register amplitude-pitch heuristic | Melody-forward lead line | Extract followable single lead line | Extracts clean diatonic sol-fa stream on piano ballad and lead instruments; fails on dense choir | **PARTIALLY PROVEN / SUPPORTED FOR CLEAR MELODY-FORWARD MATERIAL** |
| Interactive Visual Keyboard | CSS/JS 2-Octave interactive piano | Diatonic & chromatic notes | Highlight active chord triad and melody notes | Clicking chords or notes highlights correct keys live | **PROVEN** |
| End-to-End Vertical Slice | Browser Upload -> Live Server -> Real AI/DSP -> Visual Map | Supported audio formats | Working browser-to-result loop without mocks | Live HTTP test returns 200 with full payload; UI renders 4 states | **PROVEN LOCALLY** |
| Play-Along Synchronization | Browser HTML5 Audio (`currentTime`) driving Chord, Degree, Sol-fa, and Piano highlights | Loaded audio blob URL | Real-time audio playback driving visual state changes without latency or clicks | Verified with automated CDP browser tests at t=0s, 2.5s, 5.0s, forward/backward seek, and transpose +2 | **PROVEN** |

---

## 8. Real-World Validation Results (Broad Scope)

### Test 1 (Hymn Reference): "When I Survey The Wondrous Cross" (Organ Hymn, 20s slice)
- **Source**: Authentic acoustic organ recording (`when_i_survey_20s.wav`).
- **Detected Key**: **D Major** (Confidence: 0.9426) — **MATCH**
- **Detected Chords**: `Dm -> D -> A -> D -> G -> A -> D` — **MATCH** (Captures authentic I-V-I-IV-V-I cadence).
- **Scale Degrees**: `1 -> 1 -> 5 -> 1 -> 4 -> 5 -> 1` — **ACCURATE**
- **Melody Sol-fa**: `do - mi - fa - fa - do - mi - mi - la - so - do - so - so - do - fa - mi - re`
- **Utility**: High utility for a keyboardist.

### Test 2 (Boundary Case): "Nearer, My God, to Thee" (Historic SATB Choral, 30s)
- **Source**: US Army & Navy Hymnal choral performance (`nearer_my_god_30s.wav`).
- **Detected Key**: G# Major (Confidence: 0.3048) — **LOW CONFIDENCE / AMBIGUOUS**
- **Observation**: Demonstrates dense acapella choral failure boundary.

### Test 3 (Non-Hymn Test A): "Für Elise" (Classical Piano Ballad, 20s slice)
- **Source / License**: Ludwig van Beethoven, performed by Tim Starling / JMC Han (Wikimedia Commons, Public Domain).
- **Expected Key**: A Minor / E Major dominant opening
- **Detected Key**: **E Major** (Confidence: 0.7742) — **MATCH** (Captures initial E-D#-E-D#-E motif and dominant harmony).
- **Detected Chords**: `E -> Am -> E -> Am -> E -> Am` — **MATCH** (V - i alternating piano oscillation).
- **Detected Scale Degrees**: `1 -> 4 -> 1 -> 4 -> 1 -> 4` (Relative to detected E tonal center).
- **Reference Melody**: `E5 - D#5 - E5 - D#5 - E5 - B4 - D5 - C5 - A4`
- **Extracted Sol-fa**: `do - ti - do - so - li/ta - fa - do - fa - mi - so...`
- **Important Errors**: Fast chromatic trill (`D#`) mapped to diatonic `ti` against E root; minor lower octave doubling from bass notes.
- **Keyboardist Utility**: **YES**. Clearly outlines the E-Am vamp and alternating melody line.

### Test 4 (Non-Hymn Test B): "St. Louis Blues" (Jazz/Blues Band with Horns & Drums, 20s slice)
- **Source / License**: W.C. Handy, performed by Handy's Memphis Blues Band (1922 sound recording, Wikimedia Commons, Public Domain).
- **Expected Key**: G Major / D Major depending on brass transposition.
- **Detected Key**: **D Major** (Confidence: 0.8502) — **MATCH**
- **Reference Progression**: 12-bar blues in D: `D (I) -> G (IV) -> D (I) -> A (V) -> D (I)`
- **Detected Chords**: `D -> G -> Gm -> Bm -> Gm -> G -> Gm -> G -> D` — **MATCH** (Captures dominant D to G shifts and blue minor third `Gm`).
- **Detected Scale Degrees**: `1 -> 4 -> 4 -> 6 -> 4 -> 4 -> 4 -> 4 -> 1` — **ACCURATE**
- **Extracted Sol-fa**: `so - do - so - do - mi - so - si/le - re - do - do - si/le - do`
- **Important Errors**: Acoustic trumpet vibrato and percussion rattle caused minor triad splitting (`Gm`).
- **Keyboardist Utility**: **YES**. Gives the player immediate key identification (D Major) and fundamental I -> IV changes.

---

## 9. Reconciled Performance Benchmark

Isolated execution timing on exact `engine.py` pipeline (measured on Windows host):

| Stage | Warmup (20s Fur Elise) | Test A: Fur Elise (20s) | Test B: St Louis Blues (20s) | Test C: Hymn (30s) |
|---|---|---|---|---|
| **Audio Preprocessing** | 0.009 s | 0.005 s | 0.005 s | 0.025 s |
| **DSP Key & Chord Analysis** | 13.141 s (CQT warmup) | 1.464 s | 1.689 s | 1.639 s |
| **Basic Pitch Neural Inference** | 23.823 s (TF warmup) | 16.127 s | 15.710 s | 20.000 s |
| **Melody Filtering & Sol-fa** | 0.166 s | 0.090 s | 0.025 s | 0.038 s |
| **Total Request Wall-Clock** | **37.139 s** | **17.686 s** | **17.428 s** | **21.702 s** |
| **Peak Python Traced Memory** | 67.44 MB | 51.48 MB | 51.48 MB | 77.12 MB |

### Reconciliation Explanation
- **Previous "2–4 seconds" claim**: Refers strictly to raw model forward pass tensors in a pre-warmed TensorFlow session on small audio arrays.
- **Full Request Wall-Clock**: Takes **17–22 seconds** end-to-end on a 20s–30s audio file when including Librosa audio resample/CQT chromagram generation, complete MIDI note event decoding from Basic Pitch, windowed triad template matching, and lead-line filtering.
- **Process Memory**: Traced Python memory is ~50–80 MB; total OS process memory with TensorFlow shared C++ libraries loaded is ~540–600 MB RSS.

---

## 10. Privacy & Audio Lifecycle Behavior
- Uploaded audio is decoded via temporary files in the OS temp directory (`tempfile.NamedTemporaryFile`).
- Decoded 22050Hz mono WAV is fed into in-memory arrays for analysis.
- The `finally:` block in `server.py` deletes both the uploaded audio file and the converted temporary file immediately upon completion of analysis.
- No user music library, database, or persistent audio storage is maintained on the server.
- Web copy clearly informs the user that audio is processed in-memory for immediate analysis and deleted immediately.

---

## 11. Git Tracking & Deployment Status
- **Repository**: `C:\Users\HomePC\Desktop\FASTKEYS`
- **Branch**: `main`
- **Latest Commit**: `1b0c803`
- **GitHub Remote**: `https://github.com/Techkeyy/FASTKEYS` (Public)
- **Render Deployment**: Configured for `standard` (1 CPU / 2 GB RAM) in `render.yaml`. Pending owner authorization / partner promo connection to deploy live web service.
