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

def clean_txt(s):
    return str(s).replace('\u266f', '#').replace('\u266d', 'b')

def midi_to_note_clean(midi_val):
    name = librosa.midi_to_note(int(midi_val))
    return clean_txt(name)

def analyze_audio_file(audio_path: str):
    """
    Executes full FASTKEYS analysis: DSP Key + Chords + Basic Pitch AI notes + Melody Extraction.
    """
    y, sr = sf.read(audio_path)
    if y.ndim > 1:
        y = np.mean(y, axis=1) # Mono conversion
    duration = len(y) / sr
    
    # 1. Key Detection
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

    # 3. Spotify Basic Pitch Neural Transcription
    model_output, midi_data, note_events = predict(
        audio_path,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=100.0,
        minimum_frequency=None,
        maximum_frequency=None
    )
    
    all_ai_notes = []
    for start, end, midi_num, amp, _ in note_events:
        m_val = int(round(midi_num))
        interval = (m_val % 12 - root_pitch_idx) % 12
        solfa = SOLFA_MAP.get(interval, '?')
        all_ai_notes.append({
            'start': round(float(start), 2),
            'end': round(float(end), 2),
            'midi': m_val,
            'note': midi_to_note_clean(m_val),
            'amplitude': round(float(amp), 3),
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
        window_end = time_cursor + step
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
        'raw_note_count': len(all_ai_notes)
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

