(() => {
  const root=document.querySelector('[data-focus-user]');
  if(!root || !window.HTMLDialogElement || typeof HTMLDialogElement.prototype.showModal!=='function')return;
  root.hidden=false;document.querySelectorAll('[data-five-start],[data-focus-open]').forEach(b=>b.hidden=false);
  const focus=document.getElementById('focus-dialog'), park=document.getElementById('park-dialog');
  const key='studentsuccess-focus-'+root.dataset.focusUser, notesKey=key+'-notes';
  const status=document.getElementById('focus-status'), resume=document.getElementById('resume-focus');
  const pause=document.getElementById('focus-pause'), input=document.getElementById('park-text');
  let state=null, notes=[], previousFocus=null, previousPark=null;
  function read(k){try{return JSON.parse(sessionStorage.getItem(k));}catch{return null;}}
  function save(k,v){try{sessionStorage.setItem(k,JSON.stringify(v));return true;}catch{return false;}}
  const saved=read(key);
  if(saved && typeof saved.title==='string' && Number.isFinite(saved.end) && Number.isFinite(saved.remaining) && saved.remaining>=0 && saved.remaining<=600000 && Date.now()-saved.end<86400000)state=saved;
  const stored=read(notesKey);if(Array.isArray(stored))notes=stored.filter(n=>typeof n==='string'&&n.length<=300).slice(0,20);
  function remaining(){return state ? (state.paused?state.remaining:Math.max(0,state.end-Date.now())):0;}
  function render(){
    resume.hidden=!state;if(!state)return;
    document.getElementById('focus-heading').textContent=state.title;
    const left=Math.ceil(remaining()/1000);
    document.getElementById('focus-time').textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0');
    document.getElementById('focus-more').textContent=left===0?'Start 5 more minutes':'Restart 5 minutes';
    pause.disabled=left===0;pause.textContent=state.paused?'Resume':'Pause';
    const message=left===0?'Five minutes done. Stop here or choose another five.':state.paused?'Paused. Resume when you are ready.':'One small start is enough.';
    if(status.textContent!==message)status.textContent=message;
  }
  function open(){previousFocus=document.activeElement;render();if(!focus.open)focus.showModal();}
  function start(title,id){state={title,id,end:Date.now()+300000,remaining:300000,paused:false};save(key,state);open();}
  document.querySelectorAll('[data-focus-open]').forEach(b=>b.addEventListener('click',()=>{if(state){open();return;}start(b.dataset.taskTitle,b.dataset.taskId);}));
  resume.addEventListener('click',open);
  document.querySelector('[data-focus-close]').addEventListener('click',()=>focus.close());
  focus.addEventListener('close',()=>{render();previousFocus?.focus();});
  pause.addEventListener('click',()=>{state.remaining=remaining();state.paused=!state.paused;if(!state.paused)state.end=Date.now()+state.remaining;save(key,state);render();});
  document.getElementById('focus-more').addEventListener('click',()=>{if(!state)return;state.end=Date.now()+300000;state.remaining=300000;state.paused=false;save(key,state);render();});
  document.getElementById('focus-end').addEventListener('click',()=>{state=null;try{sessionStorage.removeItem(key);}catch{}focus.close();render();});
  function renderNotes(){
    const list=document.getElementById('park-list');list.replaceChildren();
    notes.forEach((text,i)=>{const li=document.createElement('li'),span=document.createElement('span'),button=document.createElement('button');span.textContent=text;button.type='button';button.className='secondary';button.textContent='Remove';button.setAttribute('aria-label','Remove thought '+(i+1));button.addEventListener('click',()=>{notes.splice(i,1);save(notesKey,notes);renderNotes();input.focus();});li.append(span,button);list.append(li);});
    document.getElementById('park-clear').hidden=notes.length===0;
  }
  document.querySelectorAll('[data-park-open]').forEach(b=>b.addEventListener('click',()=>{previousPark=document.activeElement;renderNotes();park.showModal();input.focus();}));
  document.getElementById('park-close').addEventListener('click',()=>park.close());
  park.addEventListener('close',()=>previousPark?.focus());
  document.getElementById('park-form').addEventListener('submit',event=>{event.preventDefault();const text=input.value.trim();if(!text)return;const msg=document.getElementById('park-status');if(notes.length>=20){msg.textContent='Remove a thought before adding another (20 maximum).';return;}notes.push(text);msg.textContent=save(notesKey,notes)?'Saved in this tab.':'Saved for this page only; browser storage is unavailable.';input.value='';renderNotes();input.focus();});
  document.getElementById('park-clear').addEventListener('click',()=>{notes=[];save(notesKey,notes);renderNotes();document.getElementById('park-status').textContent='Thoughts cleared.';input.focus();});
  setInterval(render,1000);document.addEventListener('visibilitychange',render);render();
  const initial=JSON.parse(document.getElementById('focus-initial').textContent);
  if(initial && typeof initial.title==='string')start(initial.title,String(initial.task_id));
})();
