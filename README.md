# FASTKEYS

**Turn an unfamiliar song into a live keyboardist play-along map.**

**[Try FASTKEYS](https://fastkeys.onrender.com)**

FASTKEYS is for the moment a keyboardist gets sent an unfamiliar song shortly before rehearsal, service, or a performance. Upload the track and follow detected chords, scale degrees, movable-do tonic solfa, lead-melody guidance, and a keyboard map that stays synchronized with playback.

> *“I know this song. What do I play when rehearsal starts in five minutes?”*

## Why FASTKEYS

A keyboardist can know the song and still have no useful starting point when the first chord is minutes away. They normally need to work out the key, chord movement, number system, melody or solfa, and practical keyboard positions separately.

FASTKEYS gives them one place to start. The original recording remains the reference while the musical map follows it.

## What FASTKEYS Does

1. **Upload a song.** Choose a recording locally or start with one of the packaged samples.
2. **Build a musical map.** Basic Pitch finds timestamped notes, then FASTKEYS adds key, chord, degree, solfa, melody, and keyboard context.
3. **Play along.** Follow the map while the original recording plays, seek to another section, or transpose the guidance for a different key.

## How It Works

```text
Upload a song
    ↓
FASTKEYS analyzes the recording
    ↓
Spotify Basic Pitch produces timestamped note events
    ↓
FASTKEYS maps harmony, melody, degrees, and solfa
    ↓
Play the original track
    ↓
The musical map follows playback
```

## Architecture

| Area | Responsibility |
|---|---|
| `server.py` | Accept uploads, normalize audio, run analysis, and clean up temporary files |
| `engine.py` | Detect key and chords, transcribe notes, reconcile overlaps, and select melody |
| `web/app.js` | Drive uploads, playback, seeking, transpose, and synchronized rendering |
| `web/music.js` | Spell notes, degrees, solfa, and keyboard guidance in musical context |
| `web/index.html` / `web/style.css` | Present the landing experience and Play-Along workspace |

## Play-Along

The workspace shows the detected key, current chord, scale degree, movable-do tonic solfa, detected lead-melody note, and chord-tone keyboard guidance. The timeline and progression lanes can be used to seek. Transpose changes the keyboard guide and notation while the recording stays in its original key.

The piano is guidance. It does not claim to reconstruct the performer's exact fingering or voicing.

## Open-Source AI at the Core

[Spotify Basic Pitch](https://github.com/spotify/basic-pitch) is the load-bearing open-source transcription component used by FASTKEYS.

```text
basic-pitch==0.4.0
```

Basic Pitch is licensed under Apache-2.0. It converts uploaded audio into timestamped note events. FASTKEYS combines those events with harmonic analysis and key-relative musical mapping to build the Play-Along timeline. Spotify does not endorse or sponsor FASTKEYS.

## Full-Song Analysis

Long recordings are analyzed in 30-second Basic Pitch chunks with 3-second overlap. FASTKEYS maps each chunk's local timestamps back to absolute song time and reconciles duplicate notes at overlap boundaries, so the returned timeline covers the recording instead of stopping at an early window.

## Synchronization

The browser's actual `audio.currentTime` is the playback clock. The interface looks up the musical state for that time, so seeking immediately updates the chord, degree, solfa, melody, and keyboard guidance together.

## Transpose

Transpose changes the pitch and chord presentation while preserving functional relationships. For example:

```text
C → D

1 → 1
```

Relative solfa remains invariant while the keyboard guide is shown in the selected key. The recording itself is not pitch-shifted.

## Tech Stack

**AI and audio**

- Spotify Basic Pitch
- TensorFlow CPU
- FFmpeg
- librosa and SoundFile

**Backend**

- Python
- FastAPI

**Frontend**

- HTML
- CSS
- JavaScript

**Deployment**

- Render

## Run Locally

Python 3.11 and FFmpeg on `PATH` are required. The same dependency set is used by the Render container.

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
.\.venv311\Scripts\python.exe server.py
```

Open <http://127.0.0.1:8000>, choose a song, or select **Try a sample**. The sample is packaged audio and uses the real analysis endpoint without an account or API key.

For the container runtime:

```sh
docker build -t fastkeys .
docker run --rm -p 8000:10000 fastkeys
```

## Tests

The core notation and synchronization regressions can be run without a browser:

```powershell
node --test test_music.cjs
.\.venv311\Scripts\python.exe -m unittest test_timing_gate test_long_song_engine -v
node --check web/app.js
node --check web/music.js
python -m py_compile server.py engine.py
git diff --check
```

The current run reports **10 passing JavaScript tests** and **6 passing Python tests**. Browser suites are available when Playwright and Chromium are installed; set `FASTKEYS_PLAYWRIGHT_MODULE`, `FASTKEYS_BROWSER`, and `FASTKEYS_SERVER_URL` when those tools are outside the default environment.

## What the Tests Try to Break

- Exact event boundaries, rests, backward and forward seeks, and the final song timestamp.
- 30-second chunk boundaries, absolute timestamps, and duplicate notes at overlap edges.
- Destination-key spelling, including flat-six display as `Bb` in a D context.
- Empty files, unsupported formats, failed analysis, and narrow mobile layouts in the broader browser suites.

## Production Proof

A 188.15-second production song was analyzed through the real Render deployment without truncation. The returned timeline remained populated near the end of the recording.

## Privacy

- Uploaded audio is processed by the FASTKEYS backend.
- The backend stores temporary server files only for analysis and deletes them during cleanup.
- FASTKEYS does not maintain a permanent uploaded-song library.
- Browser playback uses the locally selected file through a temporary object URL, which is released when the song is reset.

## Known Limitations

- Dense or heavily mixed recordings can confuse lead-melody selection.
- Chord identity can occasionally be imperfect.
- The piano visualization is guidance, not exact performer voicing or fingering.
- Multi-minute songs require meaningful processing time.
- Clear melody and harmony produce the strongest results.

## Built for a Friend

FASTKEYS was built for a real keyboardist friend who sometimes needs to learn unfamiliar songs quickly before rehearsal or performance. The product gives that moment a practical starting point without claiming to replace the musician's ears.

## Partner Technology

### Render

Render hosts the live FASTKEYS application and the Basic Pitch inference runtime.

### Backboard

Backboard was used during development and verification through R-CLI to exercise the deployed API and analysis flow.


## Credits

[Spotify Basic Pitch](https://github.com/spotify/basic-pitch), Apache-2.0.

The hero artwork is kept unchanged in the application. No separate provenance or ownership claim is made for that user-supplied artwork here.

## License

FASTKEYS does not currently declare a project-level source-code license. Third-party components retain their respective licenses.
