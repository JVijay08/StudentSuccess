(() => {
  const tools = document.getElementById('workspace-tools');
  if (!tools) return;
  const trigger = tools.querySelector('summary');
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && tools.open) {
      tools.open = false;
      trigger.focus();
    }
  });
  document.addEventListener('click', event => {
    if (tools.open && !tools.contains(event.target)) tools.open = false;
  });
})();
