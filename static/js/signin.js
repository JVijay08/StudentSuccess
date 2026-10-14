(() => {
  const form = document.getElementById('signin-form');
  if (!form) return;
  const submit = document.getElementById('signin-submit');
  const status = document.getElementById('signin-status');
  let submitting = false;
  ['username', 'password'].forEach(name => {
    const field = document.getElementById(name);
    const message = document.getElementById(`${name}-error`);
    field.addEventListener('invalid', () => {
      field.setAttribute('aria-invalid', 'true');
      message.textContent = `Enter your ${name}.`;
      message.hidden = false;
    });
    field.addEventListener('input', () => {
      field.removeAttribute('aria-invalid');
      message.hidden = true;
    });
  });
  form.addEventListener('submit', event => {
    if (submitting) { event.preventDefault(); return; }
    if (event.defaultPrevented) return;
    submitting = true;
    form.setAttribute('aria-busy', 'true');
    submit.disabled = true;
    submit.textContent = 'Signing in...';
    status.textContent = 'Opening your planner. This may take a moment if the server is waking up.';
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    form.removeAttribute('aria-busy');
    submit.disabled = false;
    submit.textContent = 'Sign in';
    status.textContent = '';
  });
  document.getElementById('signin-errors')?.focus();
})();
