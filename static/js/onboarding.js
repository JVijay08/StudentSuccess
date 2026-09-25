(() => {
  const context = document.getElementById('setup-context');
  if (!context) return;
  function update() {
    document.querySelectorAll('[data-setup-context]').forEach(group => {
      group.hidden = group.dataset.setupContext !== context.value;
      // Irrelevant values stay available if the student changes their choice.
      group.querySelectorAll('input,select').forEach(input => {input.disabled = group.hidden;});
    });
  }
  context.addEventListener('change', update);
  update();
})();
