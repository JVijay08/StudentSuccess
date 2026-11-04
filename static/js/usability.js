document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('[data-settings-search]');
  if (search) {
    search.hidden = false;
    const groups = [...document.querySelectorAll('#workspace-settings > details')];
    const original = new Map(groups.map(group => [group, group.open]));
    search.querySelector('input').addEventListener('input', event => {
      const normalize = text => text.toLocaleLowerCase().replace(/[\s_-]+/g, '');
      const query = normalize(event.target.value.trim());
      let count = 0;
      groups.forEach(group => {
        group.hidden = Boolean(query && !normalize(group.textContent).includes(query));
        group.open = query ? !group.hidden : original.get(group);
        if (!group.hidden) count++;
      });
      search.querySelector('[role=status]').textContent = query ? `${count} matching settings sections. Your changes are kept.` : '';
    });
  }

  const course = document.querySelector('[data-task-course]');
  if (course) {
    const chips = document.createElement('div');
    chips.className = 'quick-controls'; chips.setAttribute('aria-label', 'Quick course filters');
    [...course.options].slice(0, 9).forEach(option => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'secondary'; button.textContent = option.value || 'All courses';
      button.dataset.course = option.value;
      button.addEventListener('click', () => { course.value = option.value; course.dispatchEvent(new Event('change')); });
      chips.append(button);
    });
    const update = () => chips.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.course === course.value)));
    course.addEventListener('change', update); update();
    course.closest('[data-task-search]').append(chips);
  }

  const prompts = document.querySelector('[data-prompt-buttons]');
  if (prompts) {
    prompts.hidden = false;
    prompts.addEventListener('click', event => {
      const button = event.target.closest('[data-prompt]');
      if (!button) return;
      const field = document.getElementById('description');
      if (field.value.trim() && !window.confirm('Replace your current description with this example?')) return;
      field.value = button.dataset.prompt; field.dispatchEvent(new Event('input', {bubbles: true})); field.focus();
    });
  }

  const copy = document.getElementById('copy-calendar-link');
  if (copy) {
    copy.hidden = false;
    copy.addEventListener('click', async () => {
      const field = document.getElementById('calendar-feed-url');
      const message = document.getElementById('calendar-copy-status');
      try { await navigator.clipboard.writeText(field.value); message.textContent = 'Private link copied. Share it only with your calendar app.'; }
      catch (_) { field.focus(); field.select(); message.textContent = 'Copy the selected link using your browser or keyboard copy command.'; }
    });
  }

  const toc = document.getElementById('notice-contents');
  if (toc) {
    const label = document.createElement('strong'); label.textContent = 'On this page'; toc.append(label);
    const list = document.createElement('ul');
    document.querySelectorAll('.legal-sheet h2').forEach((heading, index) => {
      heading.id ||= 'notice-section-' + index;
      const li = document.createElement('li'), link = document.createElement('a');
      link.href = '#' + heading.id; link.textContent = heading.textContent; li.append(link); list.append(li);
    });
    toc.append(list); toc.hidden = false;
  }

  const storage = document.querySelector('[data-storage-inspector]');
  if (storage) {
    storage.hidden = false;
    const status = storage.querySelector('[data-storage-status]');
    const button = storage.querySelector('[data-local-backup]');
    try {
      const raw = localStorage.getItem('studentsuccess.local-plan.v1');
      const count = Object.keys(sessionStorage).filter(key => key.startsWith('studentsuccess-focus-')).length;
      status.textContent = `${raw === null ? 'No browser plan saved' : 'Browser plan: ' + (new Blob([raw]).size / 1024).toFixed(1) + ' KB'}. Focus-related entries in this tab: ${count}.`;
      button.disabled = raw === null;
    } catch (_) { status.textContent = 'Storage access is unavailable in this browser.'; button.disabled = true; }
    button.addEventListener('click', () => {
      try {
        const raw = localStorage.getItem('studentsuccess.local-plan.v1');
        if (raw === null) { status.textContent = 'No saved browser plan found.'; return; }
        const url = URL.createObjectURL(new Blob([raw], {type: 'application/json'}));
        const link = document.createElement('a'); link.href = url; link.download = 'studentsuccess-backup.json';
        document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      } catch (_) { status.textContent = 'The backup could not be downloaded. Your browser plan was not changed.'; }
    });
  }

  const form = document.querySelector('[data-task-draft-key]');
  if (form) {
    try {
      const text = sessionStorage.getItem(form.dataset.taskDraftKey);
      if (text && !form.elements.title.value) {
        form.elements.title.value = text.slice(0, 160);
        form.closest('details').open = true;
        const note = document.createElement('p'); note.setAttribute('role', 'status');
        note.textContent = 'Thought copied into a draft. Review the title, deadline, and estimate, then choose Add task. Nothing has been saved yet.';
        form.prepend(note); sessionStorage.removeItem(form.dataset.taskDraftKey);
      }
    } catch (_) { /* Normal manual entry remains available. */ }
  }

  const scenario = document.getElementById('sample-scenario');
  if (scenario) {
    scenario.hidden = false;
    const samples = [
      ['Draft your introduction', 'Composition · 45 minutes · Due tonight', 'Example: a task due within 24 hours ranks above an upcoming task.'],
      ['Review biology notes', 'Biology · 30 minutes · Deadline passed', 'Example: an overdue deadline ranks above an unstarted task due tonight.'],
      ['Draft your introduction', 'Composition · 45 minutes · In progress', 'Example: work already in progress comes first so you can finish what you started.']
    ];
    let index = 0;
    const reason = document.getElementById('sample-priority-reason'); reason.setAttribute('aria-live', 'polite');
    scenario.addEventListener('click', () => {
      index = (index + 1) % samples.length;
      const heading = document.querySelector('#preview-today h2');
      heading.textContent = samples[index][0]; heading.nextElementSibling.textContent = samples[index][1];
      reason.textContent = samples[index][2];
      const next = document.querySelector('#preview-today .notebook-row');
      next.querySelector('strong').textContent = index === 1 ? 'Draft your introduction' : 'Review biology notes';
      next.querySelector('span').textContent = index === 1 ? '45 min · Tonight' : '30 min · Tomorrow';
    });
  }
});
