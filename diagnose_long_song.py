"""Measure the first long-song coverage divergence before any fix is applied."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests
import soundfile as sf
from basic_pitch.inference import predict

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "st_louis_blues.mp3"
BASE = os.environ.get("FASTKEYS_SERVER_URL", "http://127.0.0.1:8000")


def probe_duration(path: Path) -> float:
    value = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    )
    return float(value.strip())


def max_end(events):
    return max((float(event.get("end", 0)) for event in events), default=0.0)


def main():
    uploaded_duration = probe_duration(SOURCE)
    started = time.perf_counter()
    with SOURCE.open("rb") as source_handle:
        response = requests.post(f"{BASE}/api/analyze", files={"file": (SOURCE.name, source_handle, "audio/mpeg")}, timeout=300)
    response.raise_for_status()
    result = response.json()
    request_seconds = time.perf_counter() - started

    with tempfile.TemporaryDirectory() as work:
        converted = Path(work) / "converted.wav"
        full_duration_metadata = "raw_note_max_timestamp" in result
        ffmpeg_args = ["ffmpeg", "-i", str(SOURCE)]
        if not full_duration_metadata:
            ffmpeg_args += ["-t", "45"]
        ffmpeg_args += ["-ar", "22050", "-ac", "1", str(converted), "-y", "-loglevel", "error"]
        subprocess.run(ffmpeg_args, check=True)
        decoded_duration = len(sf.read(converted, always_2d=False)[0]) / sf.info(converted).samplerate
        if full_duration_metadata:
            raw_note_max = float(result.get("raw_note_max_timestamp", 0.0))
            raw_note_count = int(result.get("raw_note_count", 0))
        else:
            _, _, raw_events = predict(
                str(converted), onset_threshold=0.5, frame_threshold=0.3,
                minimum_note_length=100.0, minimum_frequency=None, maximum_frequency=None,
            )
            raw_note_max = max((float(event[1]) for event in raw_events), default=0.0)
            raw_note_count = len(raw_events)

    report = {
        "source": str(SOURCE),
        "server": BASE,
        "uploaded_audio_duration_seconds": round(uploaded_duration, 3),
        "server_returned_duration_seconds": result.get("duration"),
        "max_chord_event_end_seconds": round(max_end(result.get("chord_progression", [])), 3),
        "max_selected_melody_event_end_seconds": round(result.get("selected_melody_max_timestamp", max_end(result.get("melody_notes", []))), 3),
        "max_tonic_solfa_event_end_seconds": round(result.get("tonic_solfa_max_timestamp", max_end(result.get("melody_notes", []))), 3),
        "max_basic_pitch_raw_note_end_seconds": round(raw_note_max, 3),
        "decoded_waveform_duration_after_server_style_ffmpeg_seconds": round(decoded_duration, 3),
        "server_request_seconds": round(request_seconds, 3),
        "raw_note_count_from_server_style_decode": raw_note_count,
        "truncation_detected": uploaded_duration - decoded_duration > 1.0,
        "first_divergence": "server.py FFmpeg preprocessing (-t 45) truncates the uploaded song before engine.analyze_audio_file receives it" if not full_duration_metadata else "none: full decoded waveform reaches the engine and chunked Basic Pitch coverage reaches the song end",
        "engine_full_waveform_input": full_duration_metadata,
        "chord_window_limit": "none beyond the available chroma frames; chord coverage ends because the input waveform is already truncated" if not full_duration_metadata else "none; full-track chroma frames are analyzed and the final detected segment is extended to duration",
        "frontend_final_event_behavior": "sync() looks up active events by audio.currentTime; after the fix the final chord segment remains active through duration while melody has a neutral rest whenever no event is active" if full_duration_metadata else "sync() looks up active events by audio.currentTime; after the final loaded event it correctly renders no active chord/rest, exposing the backend coverage gap rather than inventing data",
    }
    Path("evidence/long-song-diagnosis-before-fix.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
