"""
FASTKEYS Analysis Engine
Integrates:
1. Deterministic DSP Key Detection (Krumhansl-Schmuckler on CQT Chromagram)
2. Windowed Chord Progression Estimation (24-Triad Dot Product + smoothing)
3. Nashville/Roman Scale Degree Mapping
4. Spotify Basic Pitch Neural Note Event Extraction
5. Defensible Primary Lead-Melody Selection Heuristic
6. Diatonic Tonic Sol-fa Mapping
"""
import os
import tempfile
import time
import ctypes
import ctypes.wintypes
import numpy as np
import soundfile as sf
import librosa
from basic_pitch.inference import predict

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

SOLFA_MAP = {
    0: 'do', 1: 'di/ra', 2: 're', 3: 'ri/me', 4: 'mi',
    5: 'fa', 6: 'fi/se', 7: 'so', 8: 'si/le', 9: 'la',
    10: 'li/ta', 11: 'ti'
}
DEGREE_MAP = {0: '1', 2: '2', 4: '3', 5: '4', 7: '5', 9: '6', 11: '7'}

BASIC_PITCH_CHUNK_SECONDS = 30.0
BASIC_PITCH_OVERLAP_SECONDS = 3.0


def _current_memory_mb():
    """Return this process' resident memory without adding a runtime dependency."""
    try:
        if os.name == 'nt':
            class ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
                ]
            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
            get_process_memory_info.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), ctypes.wintypes.DWORD]
            get_process_memory_info.restype = ctypes.wintypes.BOOL
            if not get_process_memory_info(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return None
            return counters.WorkingSetSize / (1024 * 1024)
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if os.name != 'darwin' else 1)
    except Exception:
        return None

def clean_txt(s):
    return str(s).replace('\u266f', '#').replace('\u266d', 'b')

def midi_to_note_clean(midi_val):
    name = librosa.midi_to_note(int(midi_val))
    return clean_txt(name)


def _predict_note_events(audio_path):
    """Run Basic Pitch with the production thresholds used for every chunk."""
    _, _, note_events = predict(
        audio_path,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=100.0,
        minimum_frequency=None,
        maximum_frequency=None,
    )
    return note_events


def merge_overlapping_notes(events, start_tolerance=0.18):
    """Deduplicate Basic Pitch events repeated in adjacent overlapping chunks.

    Events are dictionaries with absolute ``start``/``end`` timestamps. Only
    same-pitch events from different chunks with nearly identical onsets and
    overlapping intervals are merged, so genuine repeated notes remain intact.
    """
    ordered = sorted(events, key=lambda event: (event['midi'], event['start'], event['end']))
    merged = []
    for event in ordered:
        match = None
        for previous in reversed(merged):
            if previous['midi'] != event['midi']:
                continue
            if previous.get('chunk') == event.get('chunk'):
                break
            if event['start'] - previous['start'] > start_tolerance:
                break
            overlap = min(previous['end'], event['end']) - max(previous['start'], event['start'])
            if overlap >= -0.05:
                match = previous
                break
        if match is None:
            merged.append(dict(event))
        else:
            match['start'] = min(match['start'], event['start'])
            match['end'] = max(match['end'], event['end'])
            match['amplitude'] = max(match['amplitude'], event['amplitude'])
            match['chunk'] = min(match.get('chunk', 0), event.get('chunk', 0))
    return sorted(merged, key=lambda event: (event['start'], event['midi']))


def analysis_chunk_ranges(duration, chunk_seconds=BASIC_PITCH_CHUNK_SECONDS, overlap_seconds=BASIC_PITCH_OVERLAP_SECONDS):
    """Yield sequential ``(start, end)`` ranges covering the full duration."""
    if duration <= 0:
        return
    step = chunk_seconds - overlap_seconds
    if step <= 0:
        raise ValueError('overlap_seconds must be smaller than chunk_seconds')
    start = 0.0
    while start < duration:
        end = min(duration, start + chunk_seconds)
        yield round(start, 6), round(end, 6)
        if end >= duration:
            break
        start += step


def _transcribe_basic_pitch(audio_path, y, sr, duration):
    """Transcribe a short file directly or a long file in timestamped chunks."""
    started = time.perf_counter()
    peak_memory_mb = _current_memory_mb()
    if duration <= BASIC_PITCH_CHUNK_SECONDS:
        note_events = _predict_note_events(audio_path)
        events = [
            {
                'start': max(0.0, float(start)),
                'end': min(duration, float(end)),
                'midi': int(round(midi)),
                'amplitude': float(amplitude),
                'chunk': 0,
            }
            for start, end, midi, amplitude, _ in note_events
            if float(end) > float(start)
        ]
        current_memory_mb = _current_memory_mb()
        if current_memory_mb is not None:
            peak_memory_mb = max(peak_memory_mb or 0.0, current_memory_mb)
        return events, 1, time.perf_counter() - started, peak_memory_mb

    events = []
    chunk_count = 0
    with tempfile.TemporaryDirectory(prefix='fastkeys_chunks_') as workdir:
        for chunk_start, chunk_end in analysis_chunk_ranges(duration):
            start_sample = int(round(chunk_start * sr))
            end_sample = min(len(y), int(round(chunk_end * sr)))
            chunk_path = os.path.join(workdir, f'chunk_{chunk_count:04d}.wav')
            sf.write(chunk_path, y[start_sample:end_sample], sr)
            for start, end, midi, amplitude, _ in _predict_note_events(chunk_path):
                absolute_start = max(0.0, chunk_start + float(start))
                absolute_end = min(duration, chunk_start + float(end))
                if absolute_end > absolute_start:
                    events.append({
                        'start': absolute_start,
                        'end': absolute_end,
                        'midi': int(round(midi)),
                        'amplitude': float(amplitude),
                        'chunk': chunk_count,
                    })
            current_memory_mb = _current_memory_mb()
            if current_memory_mb is not None:
                peak_memory_mb = max(peak_memory_mb or 0.0, current_memory_mb)
            chunk_count += 1

    return merge_overlapping_notes(events), chunk_count, time.perf_counter() - started, peak_memory_mb

def analyze_audio_file(audio_path: str):
    """
    Executes full FASTKEYS analysis: DSP Key + Chords + Basic Pitch AI notes + Melody Extraction.
    Basic Pitch uses sequential overlapping chunks for normal-length songs so
    every returned event remains on the original uploaded-song timeline.
    """
    analysis_started = time.perf_counter()
    y, sr = sf.read(audio_path)
    if y.ndim > 1:
        y = np.mean(y, axis=1) # Mono conversion
    duration = len(y) / sr
    
    # 1. Key Detection
    dsp_started = time.perf_counter()
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_sum = np.sum(chroma, axis=1)
    
    best_score = -float('inf')
    detected_key = "C Major"
    root_pitch_idx = 0
    key_mode = "Major"
    
    for i in range(12):
        maj_rot = np.roll(MAJOR_PROFILE, i)
        min_rot = np.roll(MINOR_PROFILE, i)
        corr_maj = np.corrcoef(chroma_sum, maj_rot)[0, 1]
        corr_min = np.corrcoef(chroma_sum, min_rot)[0, 1]
        if corr_maj > best_score:
            best_score = corr_maj
            detected_key = f"{PITCH_CLASSES[i]} Major"
            root_pitch_idx = i
            key_mode = "Major"
        if corr_min > best_score:
            best_score = corr_min
            detected_key = f"{PITCH_CLASSES[i]} Minor"
            root_pitch_idx = i
            key_mode = "Minor"

    # 2. Windowed Chord Progression
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
        similarities = np.dot(CHORD_TEMPLATES, chunk_chroma)
        best_chord_idx = np.argmax(similarities)
        conf = float(similarities[best_chord_idx])
        chord_name = CHORD_NAMES[best_chord_idx]
        
        chord_root_pc = chord_name.replace('m', '')
        c_root_idx = PITCH_CLASSES.index(chord_root_pc)
        interval = (c_root_idx - root_pitch_idx) % 12
        degree = DEGREE_MAP.get(interval, f"b{DEGREE_MAP.get((interval+1)%12, '?')}")
        if 'm' in chord_name:
            degree = degree.lower()
            
        raw_chords.append({
            'start': round(start_f * hop_length / sr, 2),
            'end': round(end_f * hop_length / sr, 2),
            'chord': chord_name,
            'degree': degree,
            'confidence': round(conf, 3)
        })

    # Merge consecutive identical chords & suppress low confidence jitter
    merged_chords = []
    for c in raw_chords:
        if not merged_chords or merged_chords[-1]['chord'] != c['chord']:
            merged_chords.append(dict(c))
        else:
            merged_chords[-1]['end'] = c['end']
            merged_chords[-1]['confidence'] = max(merged_chords[-1]['confidence'], c['confidence'])

    # Keep the final detected chord active through the end of the analyzed
    # waveform. This extends an existing segment; it never invents a chord.
    if merged_chords:
        merged_chords[-1]['end'] = round(duration, 2)

    dsp_seconds = time.perf_counter() - dsp_started

    # 3. Spotify Basic Pitch Neural Transcription. Long recordings are split
    # into overlapping chunks and converted back to absolute timestamps.
    note_events, analysis_chunks, basic_pitch_seconds, peak_memory_mb = _transcribe_basic_pitch(audio_path, y, sr, duration)
    
    all_ai_notes = []
    for event in note_events:
        start = event['start']
        end = event['end']
        m_val = event['midi']
        interval = (m_val % 12 - root_pitch_idx) % 12
        solfa = SOLFA_MAP.get(interval, '?')
        all_ai_notes.append({
            'start': round(float(start), 2),
            'end': round(float(end), 2),
            'midi': m_val,
            'note': midi_to_note_clean(m_val),
            'amplitude': round(float(event['amplitude']), 3),
            'solfa': solfa
        })

    # 4. Primary Lead Melody Selection Heuristic
    # Basic Pitch returns simultaneous chord/harmony notes and overtone harmonics.
    # To construct a clean lead melody line:
    # A. Window time into 250ms chunks (or note-onset clusters).
    # B. Filter for plausible vocal/lead keyboard register (MIDI 48 / C3 to MIDI 84 / C6).
    # C. In each active window, select the dominant lead note (highest pitch in vocal range or highest velocity).
    # D. Deduplicate and filter fleeting artifacts (< 120ms).
    
    vocal_notes = [n for n in all_ai_notes if 48 <= n['midi'] <= 84 and n['amplitude'] >= 0.35]
    vocal_notes.sort(key=lambda x: x['start'])
    
    lead_melody = []
    time_cursor = 0.0
    step = 0.25 # 250ms time window
    
    while time_cursor < duration:
        window_end = min(time_cursor + step, duration)
        candidates = [
            n for n in vocal_notes
            if max(n['start'], time_cursor) < min(n['end'], window_end)
        ]
        if candidates:
            # Score candidates: higher pitch weighted slightly for melody dominance, combined with amplitude
            best_candidate = max(candidates, key=lambda x: (x['amplitude'] * 0.7 + (x['midi'] / 127.0) * 0.3))
            
            # Check if this continues the previous note
            if not lead_melody or lead_melody[-1]['midi'] != best_candidate['midi']:
                lead_melody.append({
                    'start': round(time_cursor, 2),
                    'end': round(window_end, 2),
                    'midi': best_candidate['midi'],
                    'note': best_candidate['note'],
                    'solfa': best_candidate['solfa'],
                    'amplitude': best_candidate['amplitude']
                })
            else:
                lead_melody[-1]['end'] = round(window_end, 2)
        time_cursor += step

    # Filter out isolated short spikes (< 150ms)
    clean_melody = [n for n in lead_melody if (n['end'] - n['start']) >= 0.20]

    # Combine degree sequence summary
    degree_sequence = " -> ".join([c['degree'] for c in merged_chords[:12]])
    solfa_sequence = " - ".join([m['solfa'] for m in clean_melody[:16]])

    return {
        'filename': os.path.basename(audio_path),
        'duration': round(duration, 2),
        'key': clean_txt(detected_key),
        'key_confidence': round(float(best_score), 4),
        'chord_progression': merged_chords,
        'degree_sequence': degree_sequence,
        'melody_notes': clean_melody,
        'solfa_sequence': solfa_sequence,
        'raw_note_count': len(all_ai_notes),
        'raw_note_max_timestamp': round(max((note['end'] for note in all_ai_notes), default=0.0), 2),
        'selected_melody_max_timestamp': round(max((note['end'] for note in clean_melody), default=0.0), 2),
        'tonic_solfa_max_timestamp': round(max((note['end'] for note in clean_melody), default=0.0), 2),
        'final_chord_timestamp': round(merged_chords[-1]['end'], 2) if merged_chords else 0.0,
        'analysis_chunks': analysis_chunks,
        'analysis_chunk_seconds': BASIC_PITCH_CHUNK_SECONDS if duration > BASIC_PITCH_CHUNK_SECONDS else duration,
        'analysis_overlap_seconds': BASIC_PITCH_OVERLAP_SECONDS if duration > BASIC_PITCH_CHUNK_SECONDS else 0.0,
        'dsp_seconds': round(dsp_seconds, 3),
        'basic_pitch_seconds': round(basic_pitch_seconds, 3),
        'analysis_seconds': round(time.perf_counter() - analysis_started, 3),
        'peak_memory_mb': round(peak_memory_mb, 2) if peak_memory_mb is not None else None,
    }

if __name__ == '__main__':
    test_file = r'c:\Users\HomePC\Desktop\FASTKEYS\nearer_my_god_30s.wav'
    print(f"Testing Analysis Engine on: {test_file}")
    res = analyze_audio_file(test_file)
    print("\nResult:")
    print("Detected Key:", res['key'])
    print("Chords:", [c['chord'] for c in res['chord_progression']])
    print("Degrees:", res['degree_sequence'])
    print("Melody Sol-fa:", res['solfa_sequence'])

