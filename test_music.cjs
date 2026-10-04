const assert=require('node:assert/strict');
const {test}=require('node:test');
const M=require('./web/music.js');
test('C F G Am becomes D G A Bm; degrees remain 1 4 5 6m',()=>{
 const events=['C','F','G','Am'].map(chord=>({chord}));
 assert.deepEqual(events.map(e=>M.chord(e,'C Major',2).name),['D','G','A','Bm']);
 assert.deepEqual(events.map(e=>M.chord(e,'C Major',2).degree),['1','4','5','6m']);
});
test('transpose +2 keeps l relative while sounding A and piano MIDI become B',()=>{
 const notes=[{midi:69,start:0,end:1}];
 assert.deepEqual(M.melody(notes,0,'C Major',0),{solfa:'l',note:'A',midi:69,relative:true});
 assert.deepEqual(M.melody(notes,0,'C Major',2),{solfa:'l',note:'B',midi:71,relative:true});
 assert.equal(M.spell(71,M.keyInfo('C Major',2)),'B');
});
test('D minor uses Bb, E major uses G#, and F# major uses E#',()=>{
 assert.equal(M.chord({chord:'A#'},'D Minor').name,'Bb');
 assert.equal(M.spell(68,'E Major'),'G#');assert.equal(M.spell(65,'F# Major'),'E#');
 assert.equal(M.spell(67,'G# Minor'),'F##');
 assert.equal(M.chord({chord:'A#'},'D Minor').degree,'♭6');
});
test('functional flat-six spelling stays Bb across chord, melody, piano and transpose display',()=>{
 assert.equal(M.spell(70,M.keyInfo('D Major')),'Bb');
 assert.equal(M.chord({chord:'A#'},'D Major').name,'Bb');
 assert.equal(M.melody([{midi:70,start:0,end:1}],0,'D Major').note,'Bb');
 assert.equal(M.spell(70,M.keyInfo('C Major',2)),'Bb');
 assert.equal(M.chord({chord:'G#'},'C Major',2).name,'Bb');
 assert.equal(M.melody([{midi:68,start:0,end:1}],0,'C Major',2).note,'Bb');
});
test('do-based D natural minor produces d r me f s le te',()=>{
 const notes=[62,64,65,67,69,70,72].map((midi,i)=>({midi,start:i,end:i+1}));
 assert.deepEqual(notes.map((n,i)=>M.melody(notes,i,'D Minor').solfa),['d','r','me','f','s','le','te']);
});
test('destination key controls spelling after transposition',()=>{
 assert.equal(M.chord({chord:'G#'},'E Major',1).name,'A');
 assert.equal(M.spell(70,M.keyInfo('C Major',5)),'Bb');
});
test('ambiguous chromatic uses note name; stepwise resolution chooses one solfa',()=>{
 assert.equal(M.melody([{midi:63,start:0,end:1}],0,'C Major').solfa,'D#');
 assert.equal(M.melody([{midi:63,start:0,end:1},{midi:64,start:1,end:2}],0,'C Major').solfa,'ri');
 assert.equal(M.melody([{midi:63,start:0,end:1},{midi:62,start:1,end:2}],0,'C Major').solfa,'me');
});
test('seeks, rests and end boundaries do not retain stale highlights',()=>{
 const data={key:'C Major',chord_progression:[{chord:'C',start:1,end:2},{chord:'G',start:3,end:4}],melody_notes:[{midi:69,start:1,end:1.5}]};
 assert.equal(M.moment(data,0).chord,null);assert.equal(M.moment(data,1.5).melody,null);
 assert.equal(M.moment(data,3.1).chord.name,'G');assert.equal(M.moment(data,1.1,2).melody.note,'B');assert.equal(M.moment(data,4).chord,null);
});
test('full-duration chord coverage stays active at the final song timestamp while melody can rest',()=>{
 const data={duration:180,key:'C Major',chord_progression:[{chord:'C',start:0,end:90},{chord:'G',start:90,end:180}],melody_notes:[{midi:60,start:10,end:11}]};
 assert.equal(M.moment(data,179.99).chord.name,'G');assert.equal(M.moment(data,180).chord.name,'G');assert.equal(M.moment(data,179.99).melody,null);
});
