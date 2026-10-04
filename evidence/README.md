# FASTKEYS evidence index

These files are generated from the rebuilt local app and are the review package for the owner UAT pass.

| Evidence | What it proves |
|---|---|
| `landing-story-desktop-full.png` / `landing-story-mobile-full.png` | Complete long-page landing story after all reveal targets have entered view |
| `landing-story-desktop-{hero,problem,outputs,preview,steps,transformation,final}.png` and matching mobile files | Sequential viewport captures for the hero, problem, editorial outputs, illustrated Play-Along preview, three steps, transformation map and final CTA |
| `landing-story-proof.json` | Desktop/mobile width checks, reveal completion, inline SVG count, parallax state, asset transfer sizes and browser error collection |
| `landing-story-actions.json` | Final CTA chooser opens the native file chooser and final sample CTA reaches the existing workspace through a routed fixture |
| `landing-desktop.png` | Full-bleed hero artwork and primary import action at desktop width |
| `landing-mobile.png` | Import hierarchy at mobile width |
| `analyzing-desktop.png` | Loading state after a real upload |
| `playalong-desktop.png` | Complete Play-Along workspace with current moment, transport, lanes and piano |
| `playalong-playing.png` | Browser audio playing while guidance is rendered |
| `playalong-mobile.png` | Music-player priority at mobile width |
| `transpose-plus2.png` | DOM-level +2 transpose invariant, including sounding note and piano |
| `error-mobile.png` | Human-readable server failure state |
| `minor-playalong.png` | Real E-minor recording in the workspace |
| `chopin-minor-playing.png` | Credited Chopin E-minor recording actively playing |
| `chopin-minor-desktop.png` / `chopin-minor-mobile.png` | Minor-key workspace at desktop and mobile widths |
| `browser-proof.json` | Real upload, time progression, seek, lane selection, transpose and browser error-free proof |
| `long-song-diagnosis-before-fix.json` | Reproduction of the old 45-second backend truncation on a 188.151-second recording, including the first timestamp divergence |
| `long-song-diagnosis-after-fix.json` | Full-duration engine measurement: decoded duration, chunk count, absolute event endpoints, DSP/Basic Pitch timing and memory |
| `long-song-browser-proof.json` | Browser acceptance at 5/25/50/75/95%, final 10/5/1-second states, 10→80→35→95 seeks and real playback |
| `long-song-final-10s.png` | Final-state visual capture near the end of the 3:08 recording, with chord guidance still active and a genuine melody rest |
| `edge-proof.json` | Audible decoded samples, 320px overflow check, error, empty file, cancellation and sample flow |
| `minor-proof.json` | E-minor detection, chord and solfa sequence, playback timestamps and D-minor notation check |
| `deployment-proof.json` | Read-only production health and live-HTML comparison, when present |
| `minor-passage-selection.json` | Why the existing Für Elise recording was not used as the accepted minor-key proof |

## Verified claims

- The newest Downloads image is `C:\Users\HomePC\Downloads\download (17).jpg`; it is packaged as `web/hero.jpg` and rendered with fixed inset `0` plus `background-size: cover`.
- The rebuilt client uses the native audio element's `currentTime` for chord, degree, solfa, piano and seek state.
- The +2 regression is exact: `C | F | G | Am` becomes `D | G | A | Bm`; `1 | 4 | 5 | 6m`, `l (A)` relative solfa and piano MIDI 69 remain consistent with `l (B)` and MIDI 71.
- The credited Chopin E-minor proof detected `E Minor` at confidence `0.7877`, advanced during playback, and resynchronized after seeks at 10, 20 and 4 seconds.
- D-natural-minor presentation produces `d r me f s le te`; a functional ♭6 in D major or D minor is spelled `Bb` in the chord, melody and transposed display paths.
- The landing story remains width-safe at 1440px and 390px (`scrollWidth === innerWidth`), completes all 16 native IntersectionObserver reveals during the scroll pass, and contains four inline SVG groups. The preview progress line reports the CSS-only `previewProgress` loop. The final capture had zero page or console errors. A reduced-motion emulation pass made every reveal immediately visible, removed transitions, disabled the preview loop and parallax transform, and remained 390/390 width-safe.
- The long-song gate uses `st_louis_blues.mp3` (188.151 seconds). The fixed server returns 188.15 seconds, detects seven 30-second Basic Pitch chunks with 3-second overlap, and reports 99 chords, 110 selected melody notes and 257 raw notes. The final chord reaches 188.15 seconds; melody and tonic-solfa end earlier because the final seconds are a real rest.
- The notation-rerun browser proof measured 75.528 seconds of Basic Pitch work, 27.64 seconds of DSP, 103.463 seconds total analysis and 621.2 MB in-process peak memory. It found active chord coverage and correct rest handling at 5%, 25%, 50%, 75%, 95%, duration−10s, duration−5s and duration−1s, then resynchronized through seeks at 10%, 80%, 35% and 95%. A separate Windows working-set cross-check from the earlier full run peaked at approximately 880.31 MB.
- The first divergence was the old `ffmpeg -t 45` conversion in `server.py`: the 188.151-second source became a 45-second engine input. The fix removes that cap, analyzes the complete waveform, maps chunk-local note times back to absolute song time, deduplicates only overlapping same-pitch boundary notes, and keeps the final detected chord active through the exact duration.
- The enharmonic regression is presentation-only: raw pitch classes remain unchanged, while the accepted final section now displays `Bb Major`, degree `♭6`, solfa `Bb` and sounding note `Bb` instead of the prior `A#` spellings.

The browser run was performed on Windows with the installed Chromium and `playwright-core`. The production endpoint was checked read-only. The local 188-second run completed without an out-of-memory failure and is compatible with the configured Render standard service, but a live Render long-song run was not available; dashboard/build provenance was not available from the public HTTP surface, so the local rebuild is not claimed as deployed.
