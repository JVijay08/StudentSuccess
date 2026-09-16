/* Server time avoids relying on a misconfigured device clock. */
(() => {
  const clock = document.querySelector('[data-planner-clock]');
  if (!clock) return;
  const output = clock.querySelector('time');
  let anchor = Date.parse(output.dateTime);
  let measuredAt = performance.now();
  const zone = clock.dataset.zone;
  const dateFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: zone, year: 'numeric', month: 'numeric', day: 'numeric'
  });
  const timeFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: zone, hour: 'numeric', minute: '2-digit', hourCycle: 'h12'
  });
  function render() {
    const now = new Date(anchor + performance.now() - measuredAt);
    output.dateTime = now.toISOString();
    output.textContent = `${dateFormatter.format(now)} ${timeFormatter.format(now).replace(/\s/g, '')}`;
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
