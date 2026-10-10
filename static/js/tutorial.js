/* Guidance stays beside real controls; advancing never marks work complete. */
(() => {
  const guide = document.getElementById('tutorial-guide');
  if (!guide) return;
  const panel = document.getElementById('tutorial-panel');
  const show = document.getElementById('tutorial-show');
  const hint = document.getElementById('tutorial-hint');
  let highlighted;
  let addedTabindex = false;
  const clear = () => {
    if (highlighted) {
      highlighted.classList.remove('tutorial-target');
      if (addedTabindex) highlighted.removeAttribute('tabindex');
    }
    highlighted = null;
    addedTabindex = false;
  };
  // A new section opens its instructions. Returning from an exercise keeps the
  // student's chosen compact state, without persisting anything to the account.
  const key = `studentsuccess.tutorial.panel.${guide.dataset.step}`;
  try { if (sessionStorage.getItem(key) === 'closed') panel.open = false; } catch (_) {}
  guide.classList.add('is-docked');
  document.body.classList.add('tutorial-docked');
  const measure = () => document.documentElement.style.setProperty('--tutorial-space', `${Math.ceil(guide.getBoundingClientRect().height) + 32}px`);
  new ResizeObserver(measure).observe(guide);
  measure();
  panel.addEventListener('toggle', () => {
    measure();
    try { sessionStorage.setItem(key, panel.open ? 'open' : 'closed'); } catch (_) {}
  });
  show.hidden = false;
  show.addEventListener('click', () => {
    clear();
    const target = document.querySelector(guide.dataset.target);
    if (!target) {
      panel.open = true;
      hint.textContent = 'This control is no longer on this page. Return to this section, or choose Next section to continue.';
      return;
    }
    for (let parent = target.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    panel.open = false;
    highlighted = target;
    target.classList.add('tutorial-target');
    if (!target.matches('a,button,input,select,textarea,summary,[tabindex]')) {
      target.setAttribute('tabindex', '-1');
      addedTabindex = true;
    }
    requestAnimationFrame(() => {
      measure();
      target.focus({preventScroll: true});
      const bottom = guide.getBoundingClientRect().top;
      const rect = target.getBoundingClientRect();
      const top = window.scrollY + rect.top - Math.max(80, (bottom - Math.min(rect.height, bottom - 80)) / 2);
      const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches || document.documentElement.dataset.motion === 'reduced';
      window.scrollTo({top: Math.max(0, top), behavior: reduced ? 'instant' : 'smooth'});
    });
    hint.textContent = 'Try the outlined control. Show me and Next section stay at the bottom as you explore.';
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && highlighted) { clear(); show.focus({preventScroll: true}); }
  });
  const step = Number(guide.dataset.step);
  const report = () => {
    if (step === 1 && document.querySelector('.task-state')?.textContent.trim() === 'In progress') hint.textContent = 'Your task is now in progress. Continue when you are ready.';
    if (step === 2 && document.documentElement.dataset.paperConfirmed === 'complete') hint.textContent = 'Task completed. Today now shows your next action.';
  };
  report();
  window.addEventListener('pageshow', report);
})();
