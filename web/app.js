(() => {
  'use strict';
  const $=id=>document.getElementById(id), M=window.FastkeysMusic;
  const audio=$('browserAudioPlayer');
  let song=null, transpose=0, objectUrl=null, request=null, generation=0, frame=0, lastSignature='', currentScreen='import';
  const time=n=>`${Math.floor((Number.isFinite(n)?n:0)/60)}:${String(Math.floor((Number.isFinite(n)?n:0)%60)).padStart(2,'0')}`;
  const duration=()=>Number.isFinite(audio.duration)?audio.duration:song?.duration||0;
  function screen(name){currentScreen=name;for(const n of ['Import','Analyzing','Failed','Workspace'])$('screen'+n).hidden=n.toLowerCase()!==name;window.scrollTo(0,0);}
  function reset(){generation++;request?.abort();request=null;cancelAnimationFrame(frame);frame=0;audio.pause();audio.removeAttribute('src');audio.load();if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=null;song=null;transpose=0;lastSignature='';$('audioFileInput').value='';$('playbackNotice').textContent='';screen('import');}
  function fail(message){$('failedReasonText').textContent=message;screen('failed');}
  function sync(force=false){
    if(!song)return;
    const t=audio.currentTime,total=duration();
    $('timelineTrack').max=total||1;$('timelineTrack').value=t;
    $('currentTime').textContent=time(t);$('durationTime').textContent=time(total);
    $('momentStatus').textContent=t>song.duration+.05?'Beyond analyzed section':(audio.ended||t>=song.duration)?'Song complete':audio.paused?'Ready when you are':'Playing your song';
    const state=M.moment(song,t,transpose),signature=`${state.chordIndex}/${state.melodyIndex}/${transpose}`;
    if(!force&&signature===lastSignature)return;lastSignature=signature;
    $('currentDegree').textContent=state.chord?.degree||'·';
    $('currentChord').textContent=state.chord?state.chord.name.replace(/m$/,' Minor')+(state.chord.minor?'':' Major'):'No chord';
    $('currentSolfa').textContent=state.melody?.solfa||'·';$('currentNote').textContent=state.melody?.note||'Rest';
    for(const [id,index] of [['chordStream',state.chordIndex],['solfaStream',state.melodyIndex]]){
      const lane=$(id);for(const [i,button] of [...lane.children].entries()){
        const active=i===index,changed=button.classList.contains('active')!==active;
        button.classList.toggle('active',active);button.setAttribute('aria-current',String(active));
        if(active&&changed){const left=button.offsetLeft-lane.offsetLeft-lane.clientWidth/2+button.clientWidth/2;lane.scrollTo({left,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
      }
    }
    let melodyMidi=state.melody?.midi;
    if(melodyMidi!=null){while(melodyMidi<48)melodyMidi+=12;while(melodyMidi>72)melodyMidi-=12;}
    for(const key of $('pianoKeysBed').children){
      const midi=Number(key.dataset.midi),chord=state.chord?.tones.includes(midi%12)||false,melody=midi===melodyMidi;
      key.classList.toggle('active-chord',chord);key.classList.toggle('active-melody',melody);
      const label=M.spell(midi,M.keyInfo(song.key,transpose));key.textContent=label;
      key.setAttribute('aria-label',`${label}${Math.floor(midi/12)-1}${chord?', chord tone':''}${melody?', melody':''}`);
    }
    if(window.__FASTKEYS_TIMING_TRACE__){
      const trace=window.__fastkeysTimingTrace||(window.__fastkeysTimingTrace=[]);
      trace.push({
        performanceTime:performance.now(),audioTime:t,
        chordIndex:state.chordIndex,melodyIndex:state.melodyIndex,
        chordEvent:state.chordIndex<0?null:{...song.chord_progression[state.chordIndex]},
        melodyEvent:state.melodyIndex<0?null:{...song.melody_notes[state.melodyIndex]},
        displayedChord:$('currentChord').textContent,displayedDegree:$('currentDegree').textContent,
        displayedSolfa:$('currentSolfa').textContent,displayedNote:$('currentNote').textContent,
        highlightedPianoMidi:[...$('pianoKeysBed').children].filter(key=>key.classList.contains('active-melody')).map(key=>Number(key.dataset.midi)),
        chordPianoMidi:[...$('pianoKeysBed').children].filter(key=>key.classList.contains('active-chord')).map(key=>Number(key.dataset.midi))
      });
      if(trace.length>5000)trace.splice(0,trace.length-5000);
    }
  }
  function seek(t){if(!song)return;audio.currentTime=Math.max(0,Math.min(duration(),t));sync(true);}
  function playState(){const playing=!audio.paused&&!audio.ended;$('playText').textContent=playing?'Pause':'Play';$('playIcon').textContent=playing?'Ⅱ':'▶';cancelAnimationFrame(frame);if(playing)frame=requestAnimationFrame(tick);sync();}
  function tick(){sync();if(!audio.paused)frame=requestAnimationFrame(tick);}
  async function toggle(){if(!song)return;if(!audio.paused){audio.pause();return;}try{if(audio.ended)seek(0);await audio.play();$('playbackNotice').textContent=transpose?'Keyboard guide transposed. Recording stays in its original key.':'';}catch{$('playbackNotice').textContent='Playback could not start. Try Play again, or choose a supported audio file.';playState();}}
  function renderLanes(){
    for(const [id,events,isChord] of [['chordStream',song.chord_progression,true],['solfaStream',song.melody_notes,false]]){
      const stream=$(id);stream.replaceChildren();
      events.forEach((event,index)=>{
        const value=isChord?M.chord(event,song.key,transpose):M.melody(events,index,song.key,transpose);
        const button=document.createElement('button');button.id=`${isChord?'chord':'solfa'}-item-${index}`;
        button.className=isChord?'chord-item':'solfa-item';
        const lead=document.createElement('span'),sub=document.createElement('span');
        lead.className=isChord?'chord-item-degree':'solfa-item-syllable';sub.className=isChord?'chord-item-name':'solfa-item-note';
        lead.textContent=isChord?value.degree:value.solfa;sub.textContent=isChord?value.name:value.note;
        button.append(lead,sub);button.setAttribute('aria-label',`${lead.textContent}, ${sub.textContent}, seek to ${time(event.start)}`);button.onclick=()=>seek(event.start);stream.append(button);
      });
      if(!events.length){const empty=document.createElement('p');empty.textContent=isChord?'No clear chords detected.':'No clear melody detected.';stream.append(empty);}
    }
  }
  function transposition(offset){if(!song)return;transpose=Math.max(-12,Math.min(12,offset));$('transposeLabel').textContent=transpose>0?`+${transpose}`:String(transpose);$('wsKeyDisplay').textContent=M.keyInfo(song.key,transpose).name;$('keyLabel').textContent=transpose?'Playing key':'Detected key';$('btnTransposeDown').disabled=transpose===-12;$('btnTransposeUp').disabled=transpose===12;$('playbackNotice').textContent=transpose?'Keyboard guide transposed. Recording stays in its original key.':'';renderLanes();sync(true);}
  function validate(data){return data&&typeof data.key==='string'&&Number.isFinite(data.duration)&&data.duration>0&&Array.isArray(data.chord_progression)&&Array.isArray(data.melody_notes)&&data.chord_progression.every(e=>Number.isFinite(e.start)&&Number.isFinite(e.end)&&typeof e.chord==='string')&&data.melody_notes.every(e=>Number.isFinite(e.start)&&Number.isFinite(e.end)&&Number.isFinite(e.midi));}
  async function analyze(file,token,signal){
    if(!/\.(wav|mp3|ogg|oga|flac)$/i.test(file.name)){fail('Choose an MP3, WAV, FLAC or OGG audio file.');return;}
    if(!file.size){fail('This file is empty. Choose a recording with audio.');return;}
    $('analyzingStatusText').textContent=`Listening to ${file.name}`;
    if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(file);audio.src=objectUrl;audio.load();
    const form=new FormData();form.append('file',file);
    const response=await fetch('/api/analyze',{method:'POST',body:form,signal});
    if(!response.ok)throw new Error(response.status===400?'This recording could not be read. Try an MP3 or WAV version.':'Analysis could not finish. Please try again in a moment.');
    const data=await response.json();if(token!==generation)return;
    if(!validate(data))throw new Error('The analysis was incomplete. Please try another recording.');
    song=data;$('wsSongTitle').textContent=file.name.replace(/\.[^.]+$/,'').replaceAll('_',' ');
    $('guidanceNote').textContent=duration()>data.duration+.5?`Guidance covers the analyzed ${time(data.duration)}. Audio plays in full.`:'Follow your ears. Let the keys guide you.';
    screen('workspace');transposition(0);seek(0);$('btnPlayPause').focus({preventScroll:true});
  }
  async function begin(file,sample){
    reset();screen('analyzing');const token=generation;request=new AbortController();const signal=request.signal;
    try{if(sample){const response=await fetch(`/samples/${encodeURIComponent(sample)}`,{signal});if(!response.ok||response.headers.get('content-type')?.includes('text/html'))throw new Error('The sample could not load. Please choose a song from your device.');file=new File([await response.blob()],sample,{type:'audio/wav'});}await analyze(file,token,signal);}catch(error){if(token!==generation||error.name==='AbortError')return;fail(error.message==='Failed to fetch'?'Connection lost. Check your internet and try again.':error.message);}finally{if(token===generation)request=null;}
  }
  // Physical key geometry: 15 white keys with black keys centered on their boundaries.
  let whiteIndex=0;for(let midi=48;midi<=72;midi++){
    const black=[1,3,6,8,10].includes(midi%12),key=document.createElement('div');key.className=`piano-key key-${black?'black':'white'}`;key.id=`key-${midi}`;key.dataset.midi=midi;key.setAttribute('role','img');key.setAttribute('aria-label',M.spell(midi,'C Major'));key.style.left=`${(black?whiteIndex-.32:whiteIndex)*100/15}%`;key.style.width=`${(black?.64:1)*100/15}%`;if(!black){key.textContent=M.spell(midi,'C Major');whiteIndex++;}$('pianoKeysBed').append(key);
  }
  const chooseAudio=()=>$('audioFileInput').click(),trySample=()=>begin(null,'fixture_pop_C.wav');
  $('btnChooseAudio').onclick=chooseAudio;$('btnSample').onclick=trySample;
  document.querySelectorAll('.js-choose-audio').forEach(button=>button.addEventListener('click',event=>{event.preventDefault();chooseAudio();}));
  document.querySelectorAll('.js-try-sample').forEach(button=>button.addEventListener('click',event=>{event.preventDefault();trySample();}));
  $('audioFileInput').onchange=e=>{if(e.target.files[0])begin(e.target.files[0]);};
  for(const id of ['btnNewSong','btnCancel'])$(id).onclick=reset;
  $('btnTryAnother').onclick=()=>{reset();$('audioFileInput').click();};
  const drop=$('importDropZone');drop.ondragover=e=>{e.preventDefault();drop.classList.add('dragover');};drop.ondragleave=()=>drop.classList.remove('dragover');drop.ondrop=e=>{e.preventDefault();drop.classList.remove('dragover');if(e.dataTransfer.files[0])begin(e.dataTransfer.files[0]);};
  $('btnPlayPause').onclick=toggle;$('btnRestart').onclick=()=>seek(0);$('btnSeekBack').onclick=()=>seek(audio.currentTime-5);$('btnSeekForward').onclick=()=>seek(audio.currentTime+5);$('timelineTrack').oninput=e=>seek(Number(e.target.value));$('btnTransposeDown').onclick=()=>transposition(transpose-1);$('btnTransposeUp').onclick=()=>transposition(transpose+1);
  for(const event of ['seeking','seeked','loadedmetadata','durationchange'])audio.addEventListener(event,()=>sync(true));
  for(const event of ['play','pause','ended'])audio.addEventListener(event,playState);
  audio.addEventListener('error',()=>{if(song)$('playbackNotice').textContent='Your browser cannot play this recording. Try an MP3 or WAV version.';});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){sync(true);if(!audio.paused&&!audio.ended){cancelAnimationFrame(frame);frame=requestAnimationFrame(tick);}}});
  window.addEventListener('pageshow',()=>sync(true));
  window.addEventListener('keydown',event=>{if(currentScreen!=='workspace'||/INPUT|BUTTON|TEXTAREA|SELECT/.test(event.target.tagName)||event.target.isContentEditable)return;if(event.code==='Space'){event.preventDefault();toggle();}if(event.code==='ArrowLeft'){event.preventDefault();seek(audio.currentTime-5);}if(event.code==='ArrowRight'){event.preventDefault();seek(audio.currentTime+5);}});
  const revealObserver='IntersectionObserver' in window?new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');revealObserver.unobserve(entry.target);}}),{threshold:.14,rootMargin:'0px 0px -7%'}):null;
  document.querySelectorAll('[data-reveal],.reveal').forEach(element=>revealObserver?revealObserver.observe(element):element.classList.add('is-visible'));
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;let parallaxFrame=0;
  if(!reduced){const updateParallax=()=>{parallaxFrame=0;document.documentElement.style.setProperty('--parallax-y',`${Math.min(42,Math.max(-22,window.scrollY*.035))}px`);};window.addEventListener('scroll',()=>{if(!parallaxFrame)parallaxFrame=requestAnimationFrame(updateParallax)},{passive:true});updateParallax();}
  const sample=new URLSearchParams(location.search).get('sample');if(sample&&['fixture_pop_C.wav','fixture_lead_D.wav','when_i_survey_20s.wav'].includes(sample))begin(null,sample);
})();
