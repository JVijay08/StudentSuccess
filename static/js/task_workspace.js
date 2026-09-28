/* Search stays on this device: no query URLs, requests, or saved task text. */
(() => {
  const search = document.querySelector('[data-task-search]');
  if (!search) return;
  const cards = [...document.querySelectorAll('#task-queue [data-task-search-text]')];
  const input = search.querySelector('[data-task-query]');
  const status = search.querySelector('[data-task-search-status]');
  search.hidden = false;
  input.addEventListener('input', () => {
    const query = input.value.trim().toLocaleLowerCase();
    let count = 0;
    cards.forEach(card => {
      card.hidden = !card.dataset.taskSearchText.toLocaleLowerCase().includes(query);
      if (!card.hidden) count++;
    });
    status.textContent = query ? `${count} matching task${count === 1 ? '' : 's'}. ${count ? '' : 'Try another title or course.'}` : '';
  });
})();

(() => {const form=document.getElementById('task-form');const saved=form?.elements.saved_course;const custom=form?.elements.subject;if(!saved||!custom)return;const update=()=>{custom.disabled=Boolean(saved.value);custom.closest('label').hidden=Boolean(saved.value);};saved.addEventListener('change',update);update();})();

(() => {
  const form=document.getElementById('task-form');
  if(!form)return;
  const rule=form.elements.recurrence_rule;
  const update=()=>{
    const repeating=Boolean(rule.value);
    form.querySelector('[data-repeat-options]').hidden=!repeating;
    form.elements.repeat_start.disabled=!repeating;
    form.querySelector('[data-due-label]').textContent=repeating?'Repeat through (inclusive)':'Due date';
    form.querySelector('button[type=submit]').textContent=repeating?'Add repeating tasks':'Add task';
    form.querySelector('[data-repeat-preview]').textContent=repeating ? `Each occurrence is due at ${form.elements.due_time.value || '23:59'}, from ${form.elements.repeat_start.value || 'today'} through ${form.elements.due_at.value || 'your chosen end date'}.` : '';
  };
  ['recurrence_rule','repeat_start','due_at','due_time'].forEach(name=>form.elements[name].addEventListener('change',update));
  update();
})();
