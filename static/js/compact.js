/* Progressive disclosure on phones; original content remains usable without JS. */
(() => {
  const mobile = window.matchMedia('(max-width: 680px)');
  const groups = [];
  const selectors = '.settings-form > section, .account-grid > article, .filter-panel, .demo-checklist, .card-profile, .card-completion, .card-delay, .card-estimates, .card-history';
  document.querySelectorAll(selectors).forEach(section => {
    const title = section.querySelector('h2, h3');
    const eyebrow = section.querySelector('.eyebrow, .section-kicker');
    const label = section.classList.contains('card') && eyebrow ? eyebrow : title || eyebrow;
    if (!label) return;
    const details = document.createElement('details');
    details.className = 'mobile-disclosure';
    const summary = document.createElement('summary');
    summary.textContent = section.classList.contains('filter-panel') ? 'Filter courses' : label.textContent;
    const content = document.createElement('div');
    content.className = 'disclosure-content';
    while (section.firstChild) content.append(section.firstChild);
    details.append(summary, content);
    section.append(details);
    groups.push(details);
  });
  function adapt() {
    groups.forEach(details => {
      // Never collapse a section someone is currently editing.
      details.open = !mobile.matches || details.contains(document.activeElement) || !!details.querySelector('.errors, .form-errors');
    });
  }
  adapt();
  mobile.addEventListener('change', adapt);
  document.addEventListener('invalid', event => {
    let parent = event.target.parentElement;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
  }, true);
})();

// Deep links into task entry must reveal the form before scrolling or validation.
(() => {
  function reveal() {
    const target = document.getElementById(location.hash.slice(1));
    if (!target) return;
    for (let node = target; node; node = node.parentElement) if (node.tagName === 'DETAILS') node.open = true;
    target.scrollIntoView({block: 'start'});
    if (target.tagName === 'FORM') target.querySelector('input:not([type=hidden]),select,textarea')?.focus({preventScroll:true});
  }
  window.addEventListener('hashchange', reveal);
  document.addEventListener('click', event => { if (event.target.closest('a[href^="#"]')) setTimeout(reveal, 0); });
  if (location.hash) {
    reveal();
    window.addEventListener('load', () => requestAnimationFrame(reveal), {once:true});
  }
})();
