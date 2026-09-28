/* Paper motion is progressive enhancement. Native forms and server results stay in charge. */
(() => {
  const root = document.documentElement;
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const desktop = matchMedia('(hover: hover) and (pointer: fine)');
  const key = 'studentsuccess-paper-action-v1';
  const recentKey = 'studentsuccess-paper-course-v1';
  const animations = new Set();
  const disclosures = new Map();
  const reduced = () => preference.matches || root.dataset.motion === 'reduced';
  const validKey = value => typeof value === 'string' && /^[a-zA-Z0-9_-]{1,140}$/.test(value);
  const items = () => [...document.querySelectorAll('[data-paper-key]')];
  const item = id => items().find(node => node.dataset.paperKey === id);
  const failed = () => !!document.querySelector('.errors, .form-errors, .flash-error');
  const taskWorkspace = () => !!document.querySelector('.focus-card, .task-workspace, [data-paper-detail]');
  let outgoing, activeTransition, usedTransition = false;
  function read(storageKey, consume = true) {
    try {
      const value = JSON.parse(sessionStorage.getItem(storageKey));
      if (consume) sessionStorage.removeItem(storageKey);
      return value && Number.isFinite(value.at) && Date.now()-value.at >= 0 && Date.now()-value.at < 120000 ? value : null;
    } catch (_) { return null; }
  }
  function write(storageKey, value) {
    try { sessionStorage.setItem(storageKey, JSON.stringify(value)); } catch (_) { /* Storage is optional. */ }
  }
  function clear() {
    outgoing = null;
    try { sessionStorage.removeItem(key); } catch (_) {}
  }
  let pending = read(key);
  if (pending && (!Array.isArray(pending.before) || !Array.isArray(pending.keys) || pending.dest !== location.pathname)) pending = null;
  function animate(node, frames, duration = 180) {
    if (!node || reduced() || !node.animate) return null;
    const animation = node.animate(frames, {duration, easing:'cubic-bezier(.2,.7,.3,1)'});
    animations.add(animation);
    animation.finished.catch(() => {}).finally(() => animations.delete(animation));
    return animation;
  }
  function settle(node, offset = 4) {
    return animate(node, [{opacity:.72, transform:`translateY(${offset}px)`},{opacity:1, transform:'translateY(0)'}]);
  }
  function whenVisible(node, callback) {
    if (!node || reduced()) return;
    const rect=node.getBoundingClientRect();
    if (rect.top < innerHeight && rect.bottom > 0) { callback(); return; }
    if (!('IntersectionObserver' in window)) return;
    const observer=new IntersectionObserver(entries=>{
      if (entries.some(entry=>entry.isIntersecting)) { observer.disconnect(); callback(); }
    });
    observer.observe(node);
    window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
  }
  function mark(node) {
    if (!node || reduced()) return;
    animate(node, [{outline:'2px solid transparent'},{outline:'2px solid var(--blue)'},{outline:'2px solid transparent'}], 300);
  }
  function ink(node) {
    const heading = node?.querySelector('h1,h2,h3');
    if (!heading || reduced()) return;
    heading.classList.add('paper-ink');
    setTimeout(() => heading.classList.remove('paper-ink'), 140);
  }
  function announce(text) {
    if (!text) return;
    const status = document.createElement('p');
    status.className = 'paper-status';
    status.setAttribute('role','status');
    document.getElementById('main-content')?.append(status);
    requestAnimationFrame(() => { status.textContent = text; });
  }
  function geometry() {
    const records = [];
    for (const node of items()) {
      if (records.length === 12) break;
      const rect = node.getBoundingClientRect();
      if (!validKey(node.dataset.paperKey) || rect.width <= 0 || rect.height > innerHeight*1.1 || rect.bottom < 0 || rect.top > innerHeight) continue;
      records.push({id:node.dataset.paperKey, y:rect.top, x:rect.left, w:rect.width});
    }
    return records;
  }
  function remember(kind, id, dest, extra = {}) {
    outgoing = {kind, id, dest, from:location.pathname, at:Date.now(), before:geometry(), keys:items().map(n=>n.dataset.paperKey).filter(validKey).slice(0,300), ...extra};
    write(key, outgoing);
  }
  function capture(form) {
    const action = new URL(form.action || location.href, location.href).pathname;
    let dest = new URL(form.elements._return_to?.value || location.href, location.href).pathname;
    let match = action.match(/^\/tasks\/(\d+)\/(start|complete|undo-complete|delete|reschedule|edit|subtasks|split)$/);
    if (match) {
      if (dest.endsWith('/edit')) dest = `/tasks/${match[1]}`;
      remember(match[2], `task-${match[1]}`, dest);
    } else if (action === '/tasks') remember('add-task', '', dest);
    else if ((match = action.match(/^\/courses\/plan\/add\/([^/]+)$/))) {
      const ref = `${form.elements.catalog?.value || 'national'}-${decodeURIComponent(match[1])}`;
      remember('add-course', `course-${ref}`, dest, {ref});
    } else if ((match = action.match(/^\/courses\/plan\/(\d+)\/delete$/))) remember('remove-course', `plan-${match[1]}`, dest);
    else if (action === '/terms' || /^\/terms\/\d+\/(edit|delete)$/.test(action)) {
      dest = document.querySelector('.integrated-college-entry') ? '/courses' : '/terms';
      match = action.match(/^\/terms\/(\d+)\/(edit|delete)$/);
      remember(match ? (match[2] === 'delete' ? 'remove-course' : 'edit-course') : 'add-term', match ? `term-${match[1]}` : '', dest);
    } else if (action === '/settings') remember('settings', '', dest);
    else if (action === '/courses') remember('filter', '', '/courses');
    else clear();
  }
  function confirmed(action) {
    if (!action || action.dest !== location.pathname || failed()) return false;
    const node = item(action.id);
    if (action.kind === 'start') return node?.dataset.paperStatus === 'in_progress';
    if (action.kind === 'complete') return taskWorkspace() && (node?.dataset.paperStatus === 'completed' || (!node && !!document.querySelector('.focus-card')));
    if (action.kind === 'undo-complete') return !!node && node.dataset.paperStatus !== 'completed';
    if (action.kind === 'delete') return taskWorkspace() && !node;
    if (['add-task','subtasks','split'].includes(action.kind)) return taskWorkspace() && items().some(n=>n.dataset.paperKey.startsWith('task-') && !action.keys.includes(n.dataset.paperKey));
    if (action.kind === 'add-course') return [...document.querySelectorAll('[data-paper-course]')].some(n=>n.dataset.paperCourse === action.ref && (n.tagName === 'LI' || n.querySelector('.saved-label')));
    if (action.kind === 'add-term') return items().some(n=>n.dataset.paperKey.startsWith('term-') && !action.keys.includes(n.dataset.paperKey));
    if (action.kind === 'remove-course') return !node && !!document.querySelector('.plan-grid,.results-panel,.term-card,.college-context');
    if (['settings','edit-course','edit'].includes(action.kind)) return !!document.querySelector('.flash-success');
    if (action.kind === 'reschedule') return !!document.querySelector('form[action="/tasks/undo-schedule"]');
    if (action.kind === 'sort') return taskWorkspace();
    if (action.kind === 'filter') return !!document.querySelector('.results-heading');
    return false;
  }
  function names(transition, incoming) {
    const action = incoming ? pending : outgoing;
    if (reduced() || !action || (incoming && !confirmed(action))) { transition.skipTransition(); return; }
    const named = [];
    const ids = new Set();
    for (const record of action.before.slice(0,12)) {
      if (!validKey(record.id) || ids.has(record.id)) continue;
      const node = item(record.id);
      if (!node) continue;
      const rect = node.getBoundingClientRect();
      if (rect.width <= 0 || rect.bottom < 0 || rect.top > innerHeight || (incoming && (Math.abs(rect.top-record.y)>48 || Math.abs(rect.left-record.x)>2 || Math.abs(rect.width-record.w)>2))) continue;
      node.style.viewTransitionName = `paper-${record.id}`;
      named.push(node); ids.add(record.id);
    }
    transition.finished.finally(() => named.forEach(node=>node.style.removeProperty('view-transition-name')));
    if (incoming) {
      activeTransition = transition; usedTransition = true;
      transition.ready.catch(() => { usedTransition = false; });
    }
  }
  window.notebookMotion = {
    pageswap(event) {
      if (outgoing) { outgoing.before=geometry(); write(key,outgoing); }
      names(event.viewTransition, false);
    },
    pagereveal(event) { names(event.viewTransition, true); }
  };
  document.addEventListener('submit', event => {
    const form=event.target;
    if (form.method.toLowerCase() !== 'post') return;
    queueMicrotask(() => {
      if (event.defaultPrevented) return;
      form.setAttribute('aria-busy','true');
      capture(form);
    });
  });
  document.addEventListener('change', event => {
    if (event.target.matches('select[name=sort]')) remember('sort','','/tasks');
  }, true);
  document.addEventListener('click', event => {
    if (event.target.closest('a[href]')) clear();
  });
  function feedback() {
    root.removeAttribute('data-paper-confirmed');
    document.querySelectorAll('form[aria-busy]').forEach(form=>form.removeAttribute('aria-busy'));
    const action=pending; pending=null;
    if (confirmed(action)) {
      root.dataset.paperConfirmed=action.kind;
      if (!usedTransition && !reduced()) {
        for (const record of action.before.slice(0,12)) {
          const node=item(record.id);
          if (!node || !Number.isFinite(record.y)) continue;
          const delta=Math.max(-16,Math.min(16,record.y-node.getBoundingClientRect().top));
          if (Math.abs(delta)>1) settle(node,delta);
        }
      }
      const changed = item(action.id) || items().find(n=>!action.keys.includes(n.dataset.paperKey));
      if (action.kind === 'start') { ink(changed); settle(changed?.querySelector('.task-state,.task-tier'),0); announce('Task started.'); }
      if (action.kind === 'complete') {
        settle(document.querySelector('#completed-tasks>summary'),0);
        mark(document.querySelector('progress'));
        ink(document.querySelector('.task-overview'));
        announce('Task completed. Your next actions have been updated.');
      }
      if (['add-task','subtasks','split'].includes(action.kind)) { settle(changed); announce('Your task steps are ready.'); }
      if (action.kind === 'settings') {
        const button=document.querySelector('button[form="workspace-settings"]');
        if (button) { const original=button.textContent; button.textContent='Saved \u2713'; mark(button); setTimeout(()=>button.textContent=original,1600); }
      }
      if (['add-course','add-term','edit-course'].includes(action.kind)) {
        whenVisible(changed,()=>{ mark(changed); settle(changed); });
        write(recentKey,{at:Date.now(),ref:action.ref || '',id:changed?.dataset.paperKey || action.id});
        announce('Course saved.');
      }
      if (['filter','sort'].includes(action.kind)) settle(document.querySelector('.results-heading,.queue-heading'),0);
    } else if (!action && desktop.matches) settle(document.querySelector('.task-overview'));
    const recent=read(recentKey,false);
    if (recent && document.querySelector('.plan-grid,.term-card')) {
      const node = recent.ref ? [...document.querySelectorAll('[data-paper-course]')].find(n=>n.dataset.paperCourse===recent.ref) : item(recent.id);
      if (node) { whenVisible(node,()=>{ mark(node.closest('.year-card,.term-card')); settle(node); }); read(recentKey); }
    }
    activeTransition=null; usedTransition=false;
  }
  window.addEventListener('pageshow', () => {
    if (activeTransition) activeTransition.finished.then(feedback);
    else feedback();
  });
  // Keep native disclosure semantics and keyboard activation; animate only the size change.
  document.addEventListener('click', event => {
    const summary=event.target.closest('summary');
    const details=summary?.parentElement;
    if (!details || event.defaultPrevented || details.matches('.task-menu,#workspace-tools') || reduced() || !details.animate || event.target.closest('a,button,input,select')) return;
    event.preventDefault();
    const previous=disclosures.get(details);
    const open=previous ? !previous.open : !details.open;
    const start=details.getBoundingClientRect().height;
    previous?.finish();
    details.open=open;
    const end=details.getBoundingClientRect().height;
    details.open=true;
    details.style.overflow='clip';
    const motion=details.animate([{height:`${start}px`},{height:`${end}px`}],{duration:180,easing:'ease-out'});
    const entry={open,finish() {
      motion.cancel(); details.open=open; details.style.removeProperty('overflow'); details.style.removeProperty('height'); disclosures.delete(details);
    }};
    disclosures.set(details,entry);
    motion.finished.then(()=>entry.finish()).catch(()=>{});
  });
  document.addEventListener('toggle', event => {
    if (event.target.matches?.('.task-menu[open]')) settle(event.target.querySelector('.task-menu-panel'),-3);
  }, true);
  const stopMotion = () => {
    if (!reduced()) return;
    animations.forEach(animation=>animation.cancel());
    disclosures.forEach(entry=>entry.finish());
    document.querySelectorAll('.paper-ink').forEach(node=>node.classList.remove('paper-ink'));
    activeTransition?.skipTransition();
  };
  preference.addEventListener('change',stopMotion);
  document.querySelector('[name=reduce_motion]')?.addEventListener('change',event=>{
    root.dataset.motion=event.target.checked?'reduced':'standard'; stopMotion();
  });
  new MutationObserver(stopMotion).observe(root,{attributes:true,attributeFilter:['data-motion']});
  if (desktop.matches && !reduced() && 'IntersectionObserver' in window) {
    const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
      if (!entry.isIntersecting) return;
      observer.unobserve(entry.target);
      if (entry.target.matches('[data-paper-art=books]')) animate(entry.target,[{transform:'translateY(3px) rotate(-1deg)',opacity:.85},{transform:'none',opacity:1}],280);
      else settle(entry.target,4);
    }),{threshold:.1});
    document.querySelectorAll('.update-day,[data-paper-art=books]').forEach(node=>observer.observe(node));
  }
  let comparisons=0;
  document.addEventListener('paper:comparison',event=>{
    const count=event.detail.count;
    if (count!==comparisons) { settle(document.querySelector('.compare-tray'),3); mark(document.querySelector('#compare-count')); }
    comparisons=count;
  });
  document.getElementById('update-query')?.addEventListener('input',()=>requestAnimationFrame(()=>settle(document.getElementById('update-count'),0)));
})();
