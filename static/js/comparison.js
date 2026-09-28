(() => {
  const form = document.getElementById('compare-form');
  if (form) {
    const boxes = [...document.querySelectorAll('input[form="compare-form"][name="id"]')];
    const count = document.getElementById('compare-count');
    const selection = document.getElementById('compare-selection');
    const submit = document.querySelector('button[form="compare-form"]');
    function render(message) {
      const selected = boxes.filter(box => box.checked);
      count.textContent = message || (selected.length < 2 ? `${selected.length} selected. Choose ${2 - selected.length} more to compare.` : `${selected.length} selected. See the tradeoffs.`);
      submit.disabled = selected.length < 2;
      const tray=submit.closest('.compare-tray');
      tray.classList.toggle('has-selection', selected.length > 0);
      tray.hidden=selected.length===0;
      document.dispatchEvent(new CustomEvent('paper:comparison',{detail:{count:selected.length}}));
      selection.replaceChildren();
      selected.forEach(box => {
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = `${box.dataset.courseName} \u00d7`;
        remove.setAttribute('aria-label', `Remove ${box.dataset.courseName} from comparison`);
        remove.addEventListener('click', () => { box.checked = false; render(); box.focus(); });
        selection.append(remove);
      });
    }
    boxes.forEach(box => box.addEventListener('change', () => {
      if (boxes.filter(item => item.checked).length > 3) {
        box.checked = false;
        render('Compare up to three. Remove a selection to choose another course.');
      } else render();
    }));
    if (submit) { render(); window.addEventListener('pageshow', () => render()); }
  }
  const toggle = document.getElementById('differences-only');
  if (toggle) {
    document.getElementById('differences-control').hidden = false;
    toggle.addEventListener('change', () => {
      const rows = [...document.querySelectorAll('.comparison-table tbody tr')];
      rows.forEach(row => { row.hidden = toggle.checked && row.dataset.different === 'false'; });
      document.getElementById('no-differences').hidden = !rows.every(row => row.hidden);
    });
  }
})();
