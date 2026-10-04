import json
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

y,sr=sf.read('fur_elise.ogg')
if y.ndim>1: y=y.mean(axis=1)
profiles=[('Major',np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])),('Minor',np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]))]
names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
results=[]
for start in [30,60,90]:
    clip=librosa.resample(y[int(start*sr):int((start+30)*sr)],orig_sr=sr,target_sr=22050)
    chroma=librosa.feature.chroma_cqt(y=clip,sr=22050).sum(axis=1)
    best=max((float(np.corrcoef(chroma,np.roll(profile,i))[0,1]),names[i]+' '+mode) for mode,profile in profiles for i in range(12))
    results.append({'start':start,'seconds':30,'key':best[1],'confidence':best[0]})
    print(results[-1],flush=True)
    if best[1]=='A Minor':
        sf.write('fur_elise_minor_30s.wav',clip,22050)
        break
Path('evidence/minor-passage-selection.json').write_text(json.dumps(results,indent=2))
