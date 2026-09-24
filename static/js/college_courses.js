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
