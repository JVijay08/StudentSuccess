/* Motion communicates a change. No ambient animation or pointer-follow effects. */
(() => {
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches ||
    document.documentElement.dataset.motion === 'reduced';
  function reveal(element) {
    if (!element || reduced() || !element.animate) return;
    element.animate([{opacity: .55, transform: 'translateY(-3px)'},
      {opacity: 1, transform: 'translateY(0)'}], {duration: 160, easing: 'ease-out'});
  }
  document.addEventListener('toggle', event => {
    const details = event.target;
    if (details.tagName === 'DETAILS' && details.open) {
      const content = [...details.children].find(child => child.tagName !== 'SUMMARY');
      reveal(content);
    }
  }, true);
  reveal(document.querySelector('.flash[role="status"]'));
  // Native navigation remains in charge. Only mark valid, uncancelled submissions.
  document.addEventListener('submit', event => {
    if (event.defaultPrevented || event.target.method.toLowerCase() !== 'post') return;
    const form = event.target;
    queueMicrotask(() => {
      if (!event.defaultPrevented) form.setAttribute('aria-busy', 'true');
    });
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[aria-busy]').forEach(form => form.removeAttribute('aria-busy'));
  });
})();
