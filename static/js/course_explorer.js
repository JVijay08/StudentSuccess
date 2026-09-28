document.getElementById('catalog-scope')?.addEventListener('change', event => {
  const form=event.target.form;
  ['subject','course_type','rigor','workload','career'].forEach(name => {if(form.elements[name])form.elements[name].value='';});
});
