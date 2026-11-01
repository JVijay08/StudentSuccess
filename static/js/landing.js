(() => {
  const tabs = [...document.querySelectorAll('.preview-tabs [role="tab"]')];
  if (!tabs.length) return;
  document.querySelector('.preview-tabs').hidden = false;
  const activate = (tab, focus = false) => {
    tabs.forEach(item => {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      const panel = document.getElementById(item.getAttribute('aria-controls'));
      panel.hidden = !selected;
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', item.id);
      panel.tabIndex = 0;
      panel.classList.toggle('is-changing', selected);
    });
    if (focus) tab.focus();
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activate(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); activate(tabs[next], true); }
    });
  });
  activate(tabs[0]);
  const draft = document.getElementById('sample-draft');
  const result = document.getElementById('sample-draft-result');
  const steps = [...document.querySelectorAll('[data-sample-step]')];
  draft.hidden = false;
  result.hidden = true;
  draft.addEventListener('click', () => {
    result.hidden = false;
    draft.hidden = true;
    steps[2].focus();
    document.getElementById('sample-status').textContent = 'Example breakdown ready. Try checking off a step.';
  });
  steps.forEach(step => {
    step.disabled = false;
    step.addEventListener('change', () => {
      const done = steps.filter(item => item.checked).length;
      const text = `${done} of ${steps.length} steps complete`;
      document.getElementById('sample-progress').value = done;
      document.getElementById('sample-progress').textContent = text;
      document.querySelector('[data-sample-count]').textContent = text;
      document.getElementById('sample-status').textContent = text;
    });
  });
})();
