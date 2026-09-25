/* Search stays on this device: no query URLs, requests, or saved task text. */
(() => {
  const search = document.querySelector('[data-task-search]');
  if (!search) return;
  const cards = [...document.querySelectorAll('#task-queue [data-task-search-text]')];
  const input = search.querySelector('[data-task-query]');
  const status = search.querySelector('[data-task-search-status]');
  search.hidden = false;
  input.addEventListener('input', () => {
    const query = input.value.trim().toLocaleLowerCase();
    let count = 0;
    cards.forEach(card => {
      card.hidden = !card.dataset.taskSearchText.toLocaleLowerCase().includes(query);
      if (!card.hidden) count++;
    });
    status.textContent = query ? `${count} matching task${count === 1 ? '' : 's'}. ${count ? '' : 'Try another title or course.'}` : '';
  });
})();
