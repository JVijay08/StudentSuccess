(() => {
  const panel = document.getElementById('planner-orientation');
  const reopen = document.getElementById('orientation-reopen');
  const key = 'studentsuccess.planner-guide.v1';
  const show = visible => {panel.hidden = !visible; reopen.hidden = visible;};
  try {show(localStorage.getItem(key) !== 'dismissed');} catch (_) {show(true);}
  document.getElementById('orientation-dismiss').addEventListener('click', () => {
    try {localStorage.setItem(key, 'dismissed');} catch (_) {}
    show(false); reopen.focus();
  });
  reopen.addEventListener('click', () => {show(true); document.getElementById('orientation-dismiss').focus();});
})();
