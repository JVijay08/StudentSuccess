// The native checkbox still saves through its existing form, including without JS.
document.querySelectorAll('.bell-toggle').forEach(toggle => {
  const input = toggle.querySelector('input');
  const icon = toggle.querySelector('svg');
  let animation;
  const motionPreference = matchMedia('(prefers-reduced-motion: reduce)');
  const reduced = () => motionPreference.matches || document.documentElement.dataset.motion === 'reduced' ||
    document.querySelector('[name=reduce_motion]')?.checked;
  const stop = () => animation?.cancel();
  input.addEventListener('change', () => {
    stop();
    if (!input.checked || reduced() || !icon.animate) return;
    animation = icon.animate(
      [0, -12, 9, -5, 2, 0].map(angle => ({transform:`rotate(${angle}deg)`})),
      {duration:360,easing:'ease-out'}
    );
  });
  input.form?.addEventListener('reset', stop);
  motionPreference.addEventListener('change', stop);
  document.querySelector('[name=reduce_motion]')?.addEventListener('change', stop);
});
