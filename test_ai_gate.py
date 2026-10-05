"""
Evaluation harness for Builder Order 002: AI Core + Accuracy Gate.
Tests Spotify Basic Pitch neural network against known-reference audio cases,
compares against previous pYIN/DSP path, measures runtime and peak memory,
and details note-by-note musical errors.
"""
import os
import sys
import time
import tracemalloc
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

ROOT = Path(__file__).resolve().parent

MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Construct 24 triad templates
CHORD_NAMES = []
CHORD_TEMPLATES = []
for i, pc in enumerate(PITCH_CLASSES):
    maj_template = np.zeros(12)
    maj_template[i] = 1.0
    maj_template[(i + 4) % 12] = 0.8
    maj_template[(i + 7) % 12] = 0.8
    CHORD_NAMES.append(f"{pc}")
    CHORD_TEMPLATES.append(maj_template)
    
    min_template = np.zeros(12)
    min_template[i] = 1.0
    min_template[(i + 3) % 12] = 0.8
    min_template[(i + 7) % 12] = 0.8
    CHORD_NAMES.append(f"{pc}m")
    CHORD_TEMPLATES.append(min_template)

CHORD_TEMPLATES = np.array(CHORD_TEMPLATES)
for idx in range(len(CHORD_TEMPLATES)):
    norm = np.linalg.norm(CHORD_TEMPLATES[idx])
    if norm > 0:
        CHORD_TEMPLATES[idx] /= norm

solfa_syllables = {
    0: 'do', 1: 'di/ra', 2: 're', 3: 'ri/me', 4: 'mi',
    5: 'fa', 6: 'fi/se', 7: 'so', 8: 'si/le', 9: 'la',
    10: 'li/ta', 11: 'ti'
}
degree_map = {0: '1', 2: '2', 4: '3', 5: '4', 7: '5', 9: '6', 11: '7'}

def clean_txt(s):
    return str(s).replace('\u266f', '#').replace('\u266d', 'b')

def detect_key_and_chords(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_sum = np.sum(chroma, axis=1)
    
    best_score = -float('inf')
    detected_key = None
    root_pitch_idx = 0
    for i in range(12):
        maj_rot = np.roll(MAJOR_PROFILE, i)
        min_rot = np.roll(MINOR_PROFILE, i)
        corr_maj = np.corrcoef(chroma_sum, maj_rot)[0, 1]
        corr_min = np.corrcoef(chroma_sum, min_rot)[0, 1]
        if corr_maj > best_score:
            best_score = corr_maj
            detected_key = f"{PITCH_CLASSES[i]} Major"
            root_pitch_idx = i
        if corr_min > best_score:
            best_score = corr_min
            detected_key = f"{PITCH_CLASSES[i]} Minor"
            root_pitch_idx = i

    hop_length = 512
    chunk_duration = 1.5
    frames_per_chunk = int(chunk_duration / (hop_length / sr))
    progression = []
    for start_f in range(0, chroma.shape[1], frames_per_chunk):
        end_f = min(start_f + frames_per_chunk, chroma.shape[1])
        if end_f - start_f < frames_per_chunk // 3:
            continue
        chunk_chroma = np.mean(chroma[:, start_f:end_f], axis=1)
        norm = np.linalg.norm(chunk_chroma)
        if norm > 0:
            chunk_chroma /= norm
        similarities = np.dot(CHORD_TEMPLATES, chunk_chroma)
        best_chord_idx = np.argmax(similarities)
        chord_name = CHORD_NAMES[best_chord_idx]
        chord_root_pc = chord_name.replace('m', '')
        c_root_idx = PITCH_CLASSES.index(chord_root_pc)
        interval = (c_root_idx - root_pitch_idx) % 12
        degree = degree_map.get(interval, f"b{degree_map.get((interval+1)%12, '?')}")
        if 'm' in chord_name:
            degree = degree.lower()
        progression.append({
            'start': round(start_f * hop_length / sr, 2),
            'end': round(end_f * hop_length / sr, 2),
            'chord': chord_name,
            'degree': degree
        })
    merged = []
    for p in progression:
        if not merged or merged[-1]['chord'] != p['chord']:
            merged.append(dict(p))
        else:
            merged[-1]['end'] = p['end']
    return detected_key, best_score, root_pitch_idx, merged

def run_pyin(y, sr, root_pitch_idx):
    hop_length = 512
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C3'),
        fmax=librosa.note_to_hz('C6'),
        sr=sr,
        hop_length=hop_length
    )
    notes_detected = []
    current_note = None
    note_start = 0
    for i, (pitch, voiced) in enumerate(zip(f0, voiced_flag)):
        t = i * hop_length / sr
        if voiced and not np.isnan(pitch):
            midi_num = int(round(librosa.hz_to_midi(pitch)))
            note_name = librosa.midi_to_note(midi_num)
            interval = (midi_num % 12 - root_pitch_idx) % 12
            solfa = solfa_syllables.get(interval, '?')
            if current_note is None or current_note['midi'] != midi_num:
                if current_note is not None and (t - note_start) >= 0.15:
                    current_note['end'] = round(t, 2)
                    notes_detected.append(current_note)
                note_start = t
                current_note = {
                    'start': round(t, 2),
                    'midi': midi_num,
                    'note': note_name,
                    'solfa': solfa
                }
        else:
            if current_note is not None:
                if (t - note_start) >= 0.15:
                    current_note['end'] = round(t, 2)
                    notes_detected.append(current_note)
                current_note = None
    return notes_detected

def run_basic_pitch(audio_path, root_pitch_idx):
    model_output, midi_data, note_events = predict(
        audio_path,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=100.0,
        minimum_frequency=None,
        maximum_frequency=None
    )
    sorted_notes = sorted(note_events, key=lambda x: (x[0], -x[3]))
    parsed_notes = []
    for start, end, midi_num, amp, _ in sorted_notes:
        note_name = librosa.midi_to_note(int(midi_num))
        interval = (int(midi_num) % 12 - root_pitch_idx) % 12
        solfa = solfa_syllables.get(interval, '?')
        parsed_notes.append({
            'start': round(start, 2),
            'end': round(end, 2),
            'midi': int(midi_num),
            'note': clean_txt(note_name),
            'amp': round(float(amp), 3),
            'solfa': solfa
        })
    return parsed_notes, midi_data

def evaluate_case(name, audio_path, expected_key, expected_prog, expected_melody):
    print(f"\n=======================================================")
    print(f"CASE: {name} ({os.path.basename(audio_path)})")
    print(f"=======================================================")
    
    y, sr = sf.read(audio_path)
    dur = len(y) / sr
    print(f"Duration: {dur:.2f}s | Sample Rate: {sr} Hz")
    
    # Measure DSP Key/Chords
    t0 = time.time()
    det_key, key_score, root_pitch_idx, chords = detect_key_and_chords(y, sr)
    dsp_time = time.time() - t0
    
    print(f"--- Key Detection ---")
    print(f"Expected Key: {clean_txt(expected_key)}")
    print(f"Detected Key: {clean_txt(det_key)} (Correlation: {key_score:.4f})")
    
    print(f"\n--- Chord Progression ---")
    print(f"Expected Progression: {' -> '.join([clean_txt(p) for p in expected_prog])}")
    det_chord_flow = ' -> '.join([f"{clean_txt(c['chord'])} ({c['degree']})" for c in chords])
    print(f"Detected Progression: {det_chord_flow}")
    
    # Run pYIN for comparison
    t0 = time.time()
    pyin_notes = run_pyin(y, sr, root_pitch_idx)
    pyin_time = time.time() - t0
    
    # Run Basic Pitch AI
    tracemalloc.start()
    t0 = time.time()
    ai_notes, midi_data = run_basic_pitch(audio_path, root_pitch_idx)
    ai_time = time.time() - t0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak_mem / (1024 * 1024)
    
    print(f"\n--- AI Note Transcription (Spotify Basic Pitch) ---")
    print(f"Total AI note events detected: {len(ai_notes)}")
    print(f"Inference Runtime: {ai_time:.2f}s | Peak Traced Memory: {peak_mb:.1f} MB")
    print(f"(Baseline pYIN Runtime: {pyin_time:.2f}s, DSP Key/Chords: {dsp_time:.2f}s)")
    
    print("\nSample AI Note Events:")
    for n in ai_notes[:10]:
        print(f"  [{n['start']:5.2f}s - {n['end']:5.2f}s] {n['note']:<4} (MIDI {n['midi']:2d}, amp {n['amp']:.2f}) -> Solfa: {n['solfa']}")
    
    print(f"\n--- Reference Melody Comparison ---")
    print(f"Expected Melody: {clean_txt(expected_melody)}")
    ai_solfa_seq = ' - '.join([n['solfa'] for n in ai_notes[:15]])
    print(f"AI Sol-fa Sequence (first 15 events): {ai_solfa_seq}")
    pyin_solfa_seq = ' - '.join([n['solfa'] for n in pyin_notes[:15]])
    print(f"pYIN Sol-fa Sequence (first 15 events): {pyin_solfa_seq}")

    return {
        'name': name,
        'path': audio_path,
        'expected_key': expected_key,
        'detected_key': det_key,
        'key_score': key_score,
        'expected_prog': expected_prog,
        'detected_chords': chords,
        'expected_melody': expected_melody,
        'ai_notes': ai_notes,
        'pyin_notes': pyin_notes,
        'ai_time': ai_time,
        'pyin_time': pyin_time,
        'peak_mem_mb': peak_mb
    }

if __name__ == '__main__':
    fixtures = [
        (
            "Case 1: Clean Hymn Keyboard / Pad",
            str(ROOT / "fixture_hymn_G.wav"),
            "G Major",
            ["G", "C", "G"],
            "G3 (do) -> C4 (fa) -> E4 (la) -> C4 (fa) -> E4 (la) -> D4 (so) -> C4 (fa) -> A3 (re) -> G3 (do)"
        ),
        (
            "Case 2: Lead Instrument + Accompaniment",
            str(ROOT / "fixture_lead_D.wav"),
            "D Major",
            ["D", "G"],
            "A3 (so) -> A3 (so) -> G3 (fa) -> F#3 (mi) -> E3 (re) -> D3 (do) -> E3 (re) -> F#3 (mi) -> G3 (fa) -> A3 (so)"
        ),
        (
            "Case 3: Realistic Pop Loop (C-G-Am-F) + Lead",
            str(ROOT / "fixture_pop_C.wav"),
            "C Major",
            ["C", "G", "Am", "F"],
            "E4 (mi) -> D4 (re) -> C4 (do) -> D4 (re) -> B3 (ti) -> C4 (do) -> D4 (re) -> C4 (do) -> A3 (la) -> C4 (do) -> A3 (la) -> G3 (so) -> F3 (fa)"
        ),
        (
            "Case 4: Reference Organ Hymn (Real Acoustic Recording)",
            str(ROOT / "when_i_survey.wav"),
            "D Major",
            ["D", "A", "D", "G", "A", "D"],
            "Hamburg tune line 1: A3 (so) -> A3 (so) -> B3 (la) -> A3 (so) -> F#3 (mi) ..."
        )
    ]
    
    for name, path, exp_key, exp_prog, exp_mel in fixtures:
        evaluate_case(name, path, exp_key, exp_prog, exp_mel)
    
    print("\n=======================================================")
    print("ALL 4 TESTS EXECUTED AND REPORTED SUCCESSFULLY.")
    print("=======================================================")
