(() => {
  'use strict';
  const button = document.getElementById('use-browser-plan');
  const input = document.getElementById('browser-transfer-file');
  const status = document.getElementById('browser-transfer-status');
  if (!button || !input) return;
  button.hidden = false;
  button.addEventListener('click', () => {
    try {
      const raw = localStorage.getItem('studentsuccess.local-plan.v1');
      if (!raw) { status.textContent = 'No saved plan was found in this browser. Choose a downloaded backup instead.'; return; }
      const file = new File([raw], 'studentsuccess-browser-plan.json', {type: 'application/json'});
      if (file.size > 1024 * 1024) { status.textContent = 'This plan exceeds the 1 MB transfer limit. Your saved browser plan is unchanged.'; return; }
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      status.textContent = 'Browser plan selected. Review the destination account and choose Preview transfer.';
    } catch (_) {
      status.textContent = 'Browser storage is unavailable. Choose a downloaded backup instead.';
    }
  });
})();
