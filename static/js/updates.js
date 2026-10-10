(() => {
  const search = document.querySelector('.update-search');
  const query = document.getElementById('update-query');
  const entries = [...document.querySelectorAll('.update-entry')];
  search.hidden = false;
  query.addEventListener('input', () => {
    const words = query.value.toLocaleLowerCase().trim().split(/\s+/);
    let count = 0;
    entries.forEach(entry => {
      const text = entry.textContent.toLocaleLowerCase();
      entry.hidden = !words.every(word => text.includes(word));
      if (!entry.hidden) count++;
    });
    document.querySelectorAll('[data-update-archive]').forEach(archive => {
      archive.open = words[0] !== '' && archive.querySelector('.update-entry:not([hidden])') !== null;
      archive.hidden = !archive.querySelector('.update-entry:not([hidden])');
    });
    document.getElementById('update-count').textContent = `${count} of ${entries.length} updates`;
    document.getElementById('no-updates').hidden = count !== 0;
  });
})();
