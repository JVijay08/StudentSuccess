document.addEventListener('click', event => {
  document.querySelectorAll('.task-menu[open]').forEach(menu => {
    if (!menu.contains(event.target)) menu.open = false;
  });
});
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  const menu = event.target.closest('.task-menu[open]');
  if (menu) {menu.open = false;menu.querySelector('summary').focus();event.preventDefault();}
});
