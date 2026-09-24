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

// Enhance the same-page GET fallback without losing a draft course.
document.querySelectorAll('[data-college-finder]').forEach(form => {
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const status=form.querySelector('[role=status]');
    const button=form.querySelector('button');
    const select=document.querySelector('#term-form [name=institution_id]');
    const params=new URLSearchParams({q:form.elements.college_q.value,state:form.elements.college_state.value});
    button.disabled=true;
    status.textContent='Finding colleges...';
    try {
      const response=await fetch(form.dataset.searchUrl+'?'+params);
      if(!response.ok) throw new Error('Search unavailable');
      const data=await response.json();
      const previous=select.selectedOptions[0]?.cloneNode(true);
      select.replaceChildren(new Option('Not selected / not listed',''));
      data.results.forEach(c=>select.add(new Option(`${c.name} (${c.city}, ${c.state})`,c.id)));
      if(previous?.value && ![...select.options].some(o=>o.value===previous.value)) select.add(previous);
      select.value=previous?.value || '';
      status.textContent=`${data.total} matches${data.total>40 ? '; showing the first 40. Narrow your search for more precise results' : ''}. Choose a college below.`;
      if(data.results.length) select.focus();
    } catch {
      status.textContent='College search is unavailable. Try again, or add the course without a college for now.';
    } finally {button.disabled=false;}
  });
});
