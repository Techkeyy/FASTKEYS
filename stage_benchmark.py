"""
Clean Benchmark Harness executing the exact `engine.analyze_audio_file` pipeline.
Measures:
1. Audio loading & preprocessing
2. Basic Pitch neural network inference
3. DSP Key & Chord Analysis
4. Lead Melody selection & sol-fa conversion
5. Total wall-clock time
6. Traced peak Python memory
"""
import os
import sys
import time
import tracemalloc
import soundfile as sf
import numpy as np
import librosa
from basic_pitch.inference import predict
import engine

def measure_isolated_stages(audio_path: str):
    print(f"\n=======================================================")
    print(f"BENCHMARKING EXACT ENGINE STAGES: {os.path.basename(audio_path)}")
    print(f"=======================================================")
    
    tracemalloc.start()
    t_start = time.perf_counter()
    
    # Stage 1: Load audio
    t0 = time.perf_counter()
    y, sr = sf.read(audio_path)
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    duration = len(y) / sr
    t_load = time.perf_counter() - t0
    
    # Stage 2: DSP Key & Chord Analysis (exact code from engine.py)
    t0 = time.perf_counter()
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_sum = np.sum(chroma, axis=1)
    
    best_score = -float('inf')
    detected_key = "C Major"
    root_pitch_idx = 0
    key_mode = "Major"
    for i in range(12):
        maj_rot = np.roll(engine.MAJOR_PROFILE, i)
        min_rot = np.roll(engine.MINOR_PROFILE, i)
        corr_maj = np.corrcoef(chroma_sum, maj_rot)[0, 1]
        corr_min = np.corrcoef(chroma_sum, min_rot)[0, 1]
        if corr_maj > best_score:
            best_score = corr_maj
            detected_key = f"{engine.PITCH_CLASSES[i]} Major"
            root_pitch_idx = i
            key_mode = "Major"
        if corr_min > best_score:
            best_score = corr_min
            detected_key = f"{engine.PITCH_CLASSES[i]} Minor"
            root_pitch_idx = i
            key_mode = "Minor"

    hop_length = 512
    chunk_duration = 1.5
    frames_per_chunk = int(chunk_duration / (hop_length / sr))
    raw_chords = []
    for start_f in range(0, chroma.shape[1], frames_per_chunk):
        end_f = min(start_f + frames_per_chunk, chroma.shape[1])
        if end_f - start_f < frames_per_chunk // 3:
            continue
        chunk_chroma = np.mean(chroma[:, start_f:end_f], axis=1)
        norm = np.linalg.norm(chunk_chroma)
        if norm > 0:
            chunk_chroma /= norm
        similarities = np.dot(engine.CHORD_TEMPLATES, chunk_chroma)
        best_chord_idx = np.argmax(similarities)
        conf = float(similarities[best_chord_idx])
        chord_name = engine.CHORD_NAMES[best_chord_idx]
        chord_root_pc = chord_name.replace('m', '')
        c_root_idx = engine.PITCH_CLASSES.index(chord_root_pc)
        interval = (c_root_idx - root_pitch_idx) % 12
        degree = engine.DEGREE_MAP.get(interval, f"b{engine.DEGREE_MAP.get((interval+1)%12, '?')}")
        if 'm' in chord_name:
            degree = degree.lower()
        raw_chords.append({
            'start': round(start_f * hop_length / sr, 2),
            'end': round(end_f * hop_length / sr, 2),
            'chord': chord_name,
            'degree': degree,
            'confidence': round(conf, 3)
        })
    merged_chords = []
    for c in raw_chords:
        if not merged_chords or merged_chords[-1]['chord'] != c['chord']:
            merged_chords.append(dict(c))
        else:
            merged_chords[-1]['end'] = c['end']
            merged_chords[-1]['confidence'] = max(merged_chords[-1]['confidence'], c['confidence'])
    t_dsp = time.perf_counter() - t0
    
    # Stage 3: Spotify Basic Pitch Neural Inference
    t0 = time.perf_counter()
    model_output, midi_data, note_events = predict(
        audio_path,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=100.0,
        minimum_frequency=None,
        maximum_frequency=None
    )
    t_inference = time.perf_counter() - t0
    
    # Stage 4: Melody Filtering & Sol-fa Conversion
    t0 = time.perf_counter()
    all_ai_notes = []
    for n in note_events:
        pitch = n[2]
        start = n[0]
        end = n[1]
        amp = n[3]
        all_ai_notes.append({'pitch': pitch, 'start': start, 'end': end, 'amp': amp})
        
    lead_melody = []
    window = 0.25
    step = 0.20
    time_cursor = 0.0
    while time_cursor < duration:
        window_end = time_cursor + window
        active_notes = [n for n in all_ai_notes if n['start'] < window_end and n['end'] > time_cursor and 48 <= n['pitch'] <= 84]
        if active_notes:
            scored = sorted(active_notes, key=lambda x: (x['amp'] * 0.7 + (x['pitch'] / 127.0) * 0.3), reverse=True)
            chosen = scored[0]
            midi_pitch = int(chosen['pitch'])
            pc_idx = midi_pitch % 12
            interval = (pc_idx - root_pitch_idx) % 12
            solfa = engine.SOLFA_MAP.get(interval, '?')
            if not lead_melody or lead_melody[-1]['midi'] != midi_pitch:
                lead_melody.append({
                    'midi': midi_pitch,
                    'note': engine.midi_to_note_clean(midi_pitch),
                    'solfa': solfa,
                    'start': round(time_cursor, 2),
                    'end': round(window_end, 2)
                })
            else:
                lead_melody[-1]['end'] = round(window_end, 2)
        time_cursor += step
    clean_melody = [n for n in lead_melody if (n['end'] - n['start']) >= 0.20]
    t_melody = time.perf_counter() - t0
    
    t_total = time.perf_counter() - t_start
    curr_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"--- MEASURED TIMINGS ---")
    print(f"Duration: {duration:.2f} s")
    print(f"1. Audio Preprocessing: {t_load:.3f} s")
    print(f"2. DSP Key & Chord Analysis: {t_dsp:.3f} s")
    print(f"3. Basic Pitch Neural Inference: {t_inference:.3f} s")
    print(f"4. Melody Filtering & Sol-fa: {t_melody:.3f} s")
    print(f"Total Request Wall-Clock: {t_total:.3f} s")
    print(f"Peak Python Traced Memory: {peak_mem / (1024 * 1024):.2f} MB")
    
    print(f"\n--- ANALYSIS FINDINGS ---")
    print(f"Detected Key: {engine.clean_txt(detected_key)} (Confidence: {best_score:.4f})")
    print(f"Chords: {' -> '.join([c['chord'] for c in merged_chords[:12]])}")
    print(f"Degrees: {' -> '.join([c['degree'] for c in merged_chords[:12]])}")
    print(f"Basic Pitch Note Count: {len(all_ai_notes)}")
    print(f"Extracted Melody Notes: {len(clean_melody)}")
    print(f"Sol-fa: {' - '.join([m['solfa'] for m in clean_melody[:16]])}")
    
    return {
        'audio': os.path.basename(audio_path),
        'duration': duration,
        't_load': t_load,
        't_dsp': t_dsp,
        't_inference': t_inference,
        't_melody': t_melody,
        't_total': t_total,
        'peak_mem_mb': peak_mem / (1024 * 1024),
        'key': detected_key,
        'confidence': best_score,
        'chords': [c['chord'] for c in merged_chords],
        'degrees': [c['degree'] for c in merged_chords],
        'solfa': [m['solfa'] for m in clean_melody]
    }

if __name__ == '__main__':
    print("WARMUP RUN...")
    measure_isolated_stages("fur_elise_20s.wav")
    
    print("\n\nRUNNING NON-HYMN TEST A: fur_elise_20s.wav (Classical Piano Ballad, 20s)")
    fur_data = measure_isolated_stages("fur_elise_20s.wav")
    
    print("\n\nRUNNING NON-HYMN TEST B: st_louis_blues_20s.wav (Jazz/Blues Band with Drums & Horns, 20s)")
    blues_data = measure_isolated_stages("st_louis_blues_20s.wav")
    
    print("\n\nRUNNING 30-SECOND BENCHMARK: nearer_my_god_30s.wav (30s Audio)")
    hymn30_data = measure_isolated_stages("nearer_my_god_30s.wav")
