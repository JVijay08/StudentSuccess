document.querySelectorAll('[data-ai-generate]').forEach(form => {
  form.querySelector('[name=description]').addEventListener('input', () => { form.querySelector('[name=consent]').checked = false; });
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type=submit]');
    button.disabled = true;
    form.querySelector('[data-ai-status]').textContent = 'Drafting steps. This may take a few seconds...';
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('[data-ai-generate] button').forEach(button => { button.disabled = false; });
  document.querySelectorAll('[data-ai-status]').forEach(status => { status.textContent = ''; });
});
