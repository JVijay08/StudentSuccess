(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const precise = matchMedia('(hover: hover) and (pointer: fine)');
  const scene = document.querySelector('.desk-scene');
  const canMove = () => !reduced.matches && document.documentElement.dataset.motion !== 'reduced';
  if (scene) {
    let frame = 0;
    const reset = () => {
      cancelAnimationFrame(frame);
      scene.style.removeProperty('--tilt-x');
      scene.style.removeProperty('--tilt-y');
    };
    scene.addEventListener('pointermove', event => {
      if (!canMove() || !precise.matches) return;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (!canMove()) return;
        const rect = scene.getBoundingClientRect();
        scene.style.setProperty('--tilt-x', `${(0.5 - (event.clientY - rect.top) / rect.height) * 4}deg`);
        scene.style.setProperty('--tilt-y', `${((event.clientX - rect.left) / rect.width - 0.5) * 5}deg`);
      });
    });
    scene.addEventListener('pointerleave', reset);
    reduced.addEventListener('change', reset);
    precise.addEventListener('change', reset);
    new MutationObserver(reset).observe(document.documentElement, {attributes:true,attributeFilter:['data-motion']});
  }
  // Animate once as a section enters view; content is never hidden waiting for JS.
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        if (canMove()) entry.target.classList.add('depth-enter');
        observer.unobserve(entry.target);
      }
    }), {threshold:0.08});
    document.querySelectorAll('.notebook-story, .server-demo, .notebook-dashboard .grid>.card').forEach(el => observer.observe(el));
  }
})();
