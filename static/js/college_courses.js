(() => {
  const type = document.getElementById('enrollment-type');
  const grade = document.getElementById('dual-grade');
  if (!type || !grade) return;
  function update() {
    const dual = type.value === 'dual';
    document.getElementById('dual-grade-label').hidden = !dual;
    grade.required = dual;
    grade.disabled = !dual;
  }
  type.addEventListener('change', update);
  update();
})();

// CallChip-style feedback for the real lookup, with the same-page GET fallback intact.
document.querySelectorAll('[data-college-finder]').forEach(form => {
  const feedback = form.querySelector('[data-college-feedback]');
  const message = form.querySelector('[data-search-message]');
  const submit = form.querySelector('button[type=submit]');
  const retry = form.querySelector('[data-college-retry]');
  const select = document.querySelector('#term-form [name=institution_id]');
  if (!feedback || !message || !submit || !retry || !select) return;
  let currentRequest;
  const show = (state, text) => {
    feedback.dataset.state = state;
    message.textContent = text;
  };
  retry.addEventListener('click', () => form.requestSubmit(submit));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const searchHadFocus = form.contains(document.activeElement);
    currentRequest?.abort();
    const controller = new AbortController();
    currentRequest = controller;
    const params = new URLSearchParams({q:form.elements.college_q.value,state:form.elements.college_state.value});
    let timedOut = false;
    const timeout = setTimeout(() => {timedOut = true;controller.abort();}, 15000);
    submit.disabled = true;
    retry.disabled = true;
    select.setAttribute('aria-busy', 'true');
    show('running', 'Searching colleges... Your course draft stays here.');
    try {
      const response = await fetch(form.dataset.searchUrl + '?' + params, {signal:controller.signal});
      if (response.redirected) throw new Error('session');
      if (!response.ok) throw new Error('unavailable');
      const data = await response.json();
      if (!Array.isArray(data.results) || !Number.isInteger(data.total) || data.total < 0 ||
          data.results.some(college => ['id','name','city','state'].some(key => typeof college[key] !== 'string'))) {
        throw new Error('invalid response');
      }
      if (currentRequest !== controller) return;
      // Build everything before touching the current selection; failures keep it intact.
      const options = data.results.map(college => new Option(`${college.name} (${college.city}, ${college.state})`, college.id));
      const previous = select.selectedOptions[0]?.cloneNode(true);
      select.replaceChildren(new Option('No college selected (optional)', ''), ...options);
      if (previous?.value && !options.some(option => option.value === previous.value)) select.add(previous);
      select.value = previous?.value || '';
      const focusInSearch = searchHadFocus &&
        (document.activeElement === document.body || form.contains(document.activeElement));
      show('done', data.total
        ? `${data.total} matching college${data.total === 1 ? '' : 's'}${data.total > 40 ? '; showing the first 40. Narrow your search for more precise results' : ''}. Choose a college below.`
        : 'No colleges found. Try another name or state, or leave the college unselected.');
      retry.hidden = true;
      if (focusInSearch) {
        if (data.results.length) select.focus();
        else form.elements.college_q.focus();
      }
    } catch (error) {
      if (currentRequest !== controller) return;
      show('error', timedOut
        ? 'College search took too long. Retry, or continue without selecting a college. Your draft is unchanged.'
        : error.message === 'session'
          ? 'Your session expired. Sign in in another tab, then retry to keep this course draft.'
          : 'College search is unavailable. Retry, or continue without selecting a college. Your draft is unchanged.');
      retry.hidden = false;
    } finally {
      clearTimeout(timeout);
      if (currentRequest === controller) {
        currentRequest = null;
        submit.disabled = false;
        retry.disabled = false;
        select.removeAttribute('aria-busy');
        if (feedback.dataset.state === 'error' && searchHadFocus && document.activeElement === document.body) retry.focus();
      }
    }
  });
});
