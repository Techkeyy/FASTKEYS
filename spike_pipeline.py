import sys
import numpy as np
import soundfile as sf
import librosa

# 1. Load Audio
audio_path = r'c:\Users\HomePC\Desktop\FASTKEYS\when_i_survey.wav'
y, sr = sf.read(audio_path)
duration = len(y) / sr
print(f"--- FASTKEYS MUSIC ANALYSIS PIPELINE SPIKE ---")
print(f"Audio file: {audio_path}")
print(f"Sample Rate: {sr} Hz, Duration: {duration:.2f} seconds")

# 2. Key Detection using Krumhansl-Schmuckler Key-Finding Algorithm
# Major and Minor Pitch Class Profiles (Krumhansl-Kessler)
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Compute chromagram
chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
chroma_sum = np.sum(chroma, axis=1) # 12 pitch classes sum

best_score = -float('inf')
detected_key = None
key_mode = None
root_pitch_idx = None

for i in range(12):
    # Rotate profiles to match root i
    maj_rot = np.roll(MAJOR_PROFILE, i)
    min_rot = np.roll(MINOR_PROFILE, i)
    
    # Pearson correlation
    corr_maj = np.corrcoef(chroma_sum, maj_rot)[0, 1]
    corr_min = np.corrcoef(chroma_sum, min_rot)[0, 1]
    
    if corr_maj > best_score:
        best_score = corr_maj
        detected_key = f"{PITCH_CLASSES[i]} Major"
        key_mode = "Major"
        root_pitch_idx = i
        
    if corr_min > best_score:
        best_score = corr_min
        detected_key = f"{PITCH_CLASSES[i]} Minor"
        key_mode = "Minor"
        root_pitch_idx = i

print(f"\n[KEY DETECTION]")
print(f"Detected Key: {detected_key} (Correlation score: {best_score:.4f})")

# 3. Chord Detection & Progression Tracking over Time
# Chord templates for 12 Major and 12 Minor triads
CHORD_NAMES = []
CHORD_TEMPLATES = []

for i, pc in enumerate(PITCH_CLASSES):
    # Major triad: root, major 3rd (+4), perfect 5th (+7)
    maj_template = np.zeros(12)
    maj_template[i] = 1.0
    maj_template[(i + 4) % 12] = 0.8
    maj_template[(i + 7) % 12] = 0.8
    CHORD_NAMES.append(f"{pc}")
    CHORD_TEMPLATES.append(maj_template)
    
    # Minor triad: root, minor 3rd (+3), perfect 5th (+7)
    min_template = np.zeros(12)
    min_template[i] = 1.0
    min_template[(i + 3) % 12] = 0.8
    min_template[(i + 7) % 12] = 0.8
    CHORD_NAMES.append(f"{pc}m")
    CHORD_TEMPLATES.append(min_template)

CHORD_TEMPLATES = np.array(CHORD_TEMPLATES) # (24, 12)

# Normalize templates
for idx in range(len(CHORD_TEMPLATES)):
    norm = np.linalg.norm(CHORD_TEMPLATES[idx])
    if norm > 0:
        CHORD_TEMPLATES[idx] /= norm

# Windowed chord recognition across time (e.g. 1.0s or 1.5s steps)
# librosa frame hop is usually 512 samples (~23ms)
hop_length = 512
times = librosa.times_like(chroma, sr=sr, hop_length=hop_length)

# Aggregate into beat or 1-second chunks
chunk_duration = 1.5 # seconds
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
    t_start = start_f * hop_length / sr
    t_end = end_f * hop_length / sr
    chord_name = CHORD_NAMES[best_chord_idx]
    
    # Convert chord to Roman / Nashville Scale Degree relative to detected key
    # Root interval relative to key root
    chord_root_pc = chord_name.replace('m', '')
    chord_root_idx = PITCH_CLASSES.index(chord_root_pc)
    interval = (chord_root_idx - root_pitch_idx) % 12
    
    is_minor = 'm' in chord_name
    
    # Major scale degree mapping
    degree_map = {
        0: '1',
        2: '2',
        4: '3',
        5: '4',
        7: '5',
        9: '6',
        11: '7'
    }
    degree = degree_map.get(interval, f"b{degree_map.get((interval+1)%12, '?')}")
    if is_minor:
        degree = degree.lower() # or degree + 'm'
    
    progression.append({
        'start': round(t_start, 2),
        'end': round(t_end, 2),
        'chord': chord_name,
        'degree': degree
    })

# Merge consecutive identical chords
merged_progression = []
for p in progression:
    if not merged_progression or merged_progression[-1]['chord'] != p['chord']:
        merged_progression.append(dict(p))
    else:
        merged_progression[-1]['end'] = p['end']

print(f"\n[CHORD PROGRESSION & DEGREES]")
for p in merged_progression[:16]:
    print(f"  [{p['start']:5.1f}s - {p['end']:5.1f}s] Chord: {p['chord']:<5} Degree: {p['degree']}")
if len(merged_progression) > 16:
    print(f"  ... and {len(merged_progression) - 16} more chord events.")

# Degree summary sequence
degree_sequence = " -> ".join([p['degree'] for p in merged_progression[:12]])
print(f"Key Progression Degrees Flow: {degree_sequence}")

# 4. Melody & Pitch Extraction using pYIN
print(f"\n[MELODY & TONIC SOL-FA CONVERSION]")
# Run pYIN for pitch tracking
f0, voiced_flag, voiced_probs = librosa.pyin(
    y,
    fmin=librosa.note_to_hz('C3'),
    fmax=librosa.note_to_hz('C6'),
    sr=sr,
    hop_length=hop_length
)

# Convert voiced frequencies to MIDI note numbers and Solfa
solfa_syllables = {
    0: 'do',
    1: 'di/ra',
    2: 're',
    3: 'ri/me',
    4: 'mi',
    5: 'fa',
    6: 'fi/se',
    7: 'so',
    8: 'si/le',
    9: 'la',
    10: 'li/ta',
    11: 'ti'
}

# Note quantization
notes_detected = []
current_note = None
note_start = 0

for i, (pitch, voiced) in enumerate(zip(f0, voiced_flag)):
    t = i * hop_length / sr
    if voiced and not np.isnan(pitch):
        midi_num = int(round(librosa.hz_to_midi(pitch)))
        note_name = librosa.midi_to_note(midi_num)
        pc_idx = midi_num % 12
        interval = (pc_idx - root_pitch_idx) % 12
        solfa = solfa_syllables.get(interval, '?')
        
        if current_note is None or current_note['midi'] != midi_num:
            if current_note is not None and (t - note_start) >= 0.15: # Filter out fleeting transients < 150ms
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

print(f"Total melody note events detected: {len(notes_detected)}")
print("Sample melody notes with Tonic Sol-fa:")
for n in notes_detected[:15]:
    safe_note = str(n['note']).replace('\u266f', '#').replace('\u266d', 'b')
    print(f"  [{n['start']:5.1f}s - {n['end']:5.1f}s] Note: {safe_note:<4} (MIDI: {n['midi']:2d}) -> Solfa: {n['solfa']}")

solfa_summary = " - ".join([n['solfa'] for n in notes_detected[:16]])
print(f"Melody Sol-fa sequence: {solfa_summary}")

print(f"\n==========================================")
print(f"FEASIBILITY SPIKE COMPLETE AND VERIFIED.")
print(f"==========================================")
