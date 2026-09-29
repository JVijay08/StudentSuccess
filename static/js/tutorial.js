/* Guidance only: actions stay in the real forms, and progress stays on the server. */
(() => {
  const guide=document.getElementById('tutorial-guide');
  if (!guide) return;
  const show=document.getElementById('tutorial-show');
  const hint=document.getElementById('tutorial-hint');
  const back=document.createElement('button');
  back.type='button';back.textContent='Back to tutorial';back.className='tutorial-return';back.hidden=true;
  document.body.append(back);
  back.addEventListener('click',()=>{clear();document.getElementById('tutorial-panel').open=true;show.focus();guide.scrollIntoView({block:'start',behavior:'instant'});});
  let highlighted;
  const clear=()=>{highlighted?.classList.remove('tutorial-target');highlighted=null;back.hidden=true;};
  show.hidden=false;
  show.addEventListener('click',()=>{
    clear();
    const target=document.querySelector(guide.dataset.target);
    if (!target) {
      hint.textContent='This control may have changed after your action. Use Return to this section, or continue to the next section when ready.';
      return;
    }
    for(let parent=target.parentElement;parent;parent=parent.parentElement) if(parent.tagName==='DETAILS') parent.open=true;
    highlighted=target;
    back.hidden=false;
    target.classList.add('tutorial-target');
    if (!target.matches('a,button,input,select,textarea,summary,[tabindex]')) target.setAttribute('tabindex','-1');
    target.focus({preventScroll:true});
    target.scrollIntoView({behavior:'instant',block:'center'});
    hint.textContent='The outlined control is ready to try. The guide remains above the page; use Next section when you are ready.';
  });
  document.addEventListener('keydown',event=>{if(event.key==='Escape' && highlighted) {clear();show.focus();}});
  // Report actual returned state, never infer completion from clicking Next.
  const step=Number(guide.dataset.step);
  if(step===1 && document.querySelector('.task-state')?.textContent.trim()==='In progress') hint.textContent='Your task is now in progress. Continue when you are ready.';
  if(step===2 && document.documentElement.dataset.paperConfirmed==='complete') hint.textContent='Task completed. Today now shows your next action.';
  window.addEventListener('pageshow',()=>{
    if(step===2 && document.documentElement.dataset.paperConfirmed==='complete') hint.textContent='Task completed. Today now shows your next action.';
  });
})();
