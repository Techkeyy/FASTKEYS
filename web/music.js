/* Pure presentation theory. Detection and inference remain in engine.py. */
(function (root) {
  'use strict';
  const sharp = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
  const flat = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
  const mod = n => ((n % 12) + 12) % 12;
  const pc = name => {
    const m = String(name).replaceAll('♯','#').replaceAll('♭','b').match(/^([A-G])([#b]*)/);
    if (!m) return 0;
    return mod({C:0,D:2,E:4,F:5,G:7,A:9,B:11}[m[1]] + [...m[2]].reduce((s,a)=>s+(a==='#'?1:-1),0));
  };
  function keyInfo(name, offset=0) {
    const minor = /minor/i.test(name);
    const tonic = mod(pc(name)+offset);
    const names = minor ? ['C','C#','D','Eb','E','F','F#','G','G#','A','Bb','B'] : ['C','Db','D','Eb','E','F','F#','G','Ab','A','Bb','B'];
    const rootName = names[tonic];
    return {tonic, minor, root:rootName, name:`${rootName} ${minor?'Minor':'Major'}`, flats:(minor?[0,2,3,5,7,10]:[1,3,5,8,10]).includes(tonic)};
  }
  const degreeLabels = ['1','♭2','2','♭3','3','4','♯4','5','♭6','6','♭7','7'];
  function spell(pitch, key) {
    const k = typeof key === 'string' ? keyInfo(key) : key;
    const steps = k.minor ? [0,2,3,5,7,8,10] : [0,2,4,5,7,9,11];
    const interval = mod(pitch-k.tonic);
    const degree = k.minor && interval===11 ? 6 : steps.indexOf(interval);
    if (degree >= 0) {
      const letters = ['C','D','E','F','G','A','B'];
      const letter = letters[(letters.indexOf(k.root[0])+degree)%7];
      let delta = mod(pitch-pc(letter));
      if (delta>6) delta-=12;
      return letter + (delta>0?'#'.repeat(delta):'b'.repeat(-delta));
    }
    // Preserve the functional accidental in the established key context.
    // For example, D-major pitch class 10 is ♭6 and must display as Bb,
    // even though the detector may have supplied the enharmonic A# spelling.
    const functionalDegree = degreeLabels[interval];
    // Keep the existing sharp/flat policy for other ambiguous chromatic
    // pitches, while making the ♭6 case explicit across major-key displays.
    if (functionalDegree === '♭6') return flat[mod(pitch)];
    return (k.flats?flat:sharp)[mod(pitch)];
  }
  const degree = (interval, minor=false) => degreeLabels[mod(interval)]+(minor?'m':'');
  function chord(event, originalKey, offset=0) {
    const minor = /m$/.test(event.chord);
    const root = pc(event.chord);
    const shifted = mod(root+offset);
    return {name:spell(shifted,keyInfo(originalKey,offset))+(minor?'m':''), degree:degree(root-pc(originalKey),minor), minor, tones:[shifted,mod(shifted+(minor?3:4)),mod(shifted+7)]};
  }
  function melody(notes, index, originalKey, offset=0) {
    const note = notes[index];
    const k = keyInfo(originalKey);
    const interval = mod(note.midi-k.tonic);
    const stable = k.minor ? {0:'d',2:'r',3:'me',5:'f',7:'s',8:'le',10:'te',11:'t'} : {0:'d',2:'r',4:'m',5:'f',7:'s',9:'l',11:'t'};
    let solfa = stable[interval];
    const sounding = spell(note.midi+offset,keyInfo(originalKey,offset));
    if (!solfa) {
      // A close stepwise resolution supplies direction; ambiguous notes use pitch names.
      const next = notes[index+1];
      const delta = next && next.start-note.end <= .5 ? next.midi-note.midi : 0;
      const raised = {1:'di',3:'ri',6:'fi',8:'si',10:'li'};
      const lowered = {1:'ra',3:'me',6:'se',8:'le',10:'te'};
      solfa = delta>0 && delta<=2 ? raised[interval] : delta<0 && delta>=-2 ? lowered[interval] : null;
      if (k.minor && interval===4 && delta===1) solfa='m';
      if (k.minor && interval===9 && delta>0 && delta<=2) solfa='l';
    }
    return {solfa:solfa||sounding, note:sounding, midi:note.midi+offset, relative:!!solfa};
  }
  function findEventIndex(events,time,duration=0,includeFinal=false) {
    let low=0,high=events.length-1,candidate=-1;
    while(low<=high){
      const middle=(low+high)>>1;
      if(time>=events[middle].start){candidate=middle;low=middle+1;}
      else high=middle-1;
    }
    if(candidate<0)return -1;
    const event=events[candidate],last=candidate===events.length-1;
    return time<event.end||(includeFinal&&last&&time<=duration)?candidate:-1;
  }
  function moment(data,time,offset=0) {
    const chordIndex=findEventIndex(data.chord_progression,time,data.duration,true);
    const melodyIndex=findEventIndex(data.melody_notes,time,0,false);
    return {chordIndex,melodyIndex,chord:chordIndex<0?null:chord(data.chord_progression[chordIndex],data.key,offset),melody:melodyIndex<0?null:melody(data.melody_notes,melodyIndex,data.key,offset)};
  }
  const api={mod,pc,keyInfo,spell,degree,chord,melody,findEventIndex,moment};
  if (typeof module !== 'undefined') module.exports=api;
  root.FastkeysMusic=api;
})(globalThis);
