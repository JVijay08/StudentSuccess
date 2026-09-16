/* Server time avoids relying on a misconfigured device clock. */
(() => {
  const clock = document.querySelector('[data-planner-clock]');
  if (!clock) return;
  const output = clock.querySelector('time');
  let anchor = Date.parse(output.dateTime);
  let measuredAt = performance.now();
  const zone = clock.dataset.zone;
  const dateFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: zone, year: 'numeric', month: 'short', day: '2-digit', weekday: 'long'
  });
  const numericDate = new Intl.DateTimeFormat('en-US', {
    timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit'
  });
  const timeFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: zone, hour: '2-digit', minute: '2-digit', second: '2-digit',
    hourCycle: clock.dataset.timeFormat === '24-hour' ? 'h23' : 'h12',
    timeZoneName: 'short'
  });
  function render() {
    const now = new Date(anchor + performance.now() - measuredAt);
    const parts = Object.fromEntries(dateFormatter.formatToParts(now).map(p => [p.type, p.value]));
    let date = `${parts.month} ${parts.day}, ${parts.year}`;
    if (clock.dataset.dateFormat === 'day-first') date = `${parts.day} ${parts.month} ${parts.year}`;
    if (clock.dataset.dateFormat === 'year-first') {
      const digits = Object.fromEntries(numericDate.formatToParts(now).map(p => [p.type, p.value]));
      date = `${digits.year}-${digits.month}-${digits.day}`;
    }
    output.dateTime = now.toISOString();
    output.textContent = `${parts.weekday}, ${date} · ${timeFormatter.format(now)}`;
  }
  let syncing = false;
  async function sync() {
    if (syncing || document.hidden) return;
    syncing = true;
    const start = performance.now();
    try {
      const response = await fetch(clock.dataset.timeUrl, {cache: 'no-store'});
      if (!response.ok) return;
      const data = await response.json();
      const stamp = Date.parse(data.utc);
      if (!Number.isFinite(stamp)) return;
      measuredAt = performance.now();
      anchor = stamp + (measuredAt - start) / 2;
      render();
    } catch (_) {
      // Keep the last server-based clock running during temporary network loss.
    } finally {
      syncing = false;
    }
  }
  render();
  sync();
  window.setInterval(render, 1000);
  window.setInterval(sync, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) sync(); });
  window.addEventListener('pageshow', sync);
})();
