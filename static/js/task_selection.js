(() => {
  const form=document.getElementById('task-selection');
  if(!form)return;
  const rows=[...form.querySelectorAll('.selection-row')];
  const search=document.getElementById('selection-search');
  const status=document.getElementById('selection-status');
  let last=null;
  form.addEventListener('click',event=>{
    const box=event.target.closest('input[name=task_ids]');
    if(!box)return;
    const visible=rows.filter(row=>!row.hidden).map(row=>row.querySelector('input'));
    if(event.shiftKey && visible.includes(last)){
      const from=visible.indexOf(last),to=visible.indexOf(box);
      visible.slice(Math.min(from,to),Math.max(from,to)+1).forEach(input=>input.checked=box.checked);
    }
    last=box;
    update();
  });
  const update=()=>{
    const query=search.value.trim().toLocaleLowerCase();
    let visible=0,selected=0,hiddenSelected=0;
    rows.forEach(row=>{
      row.hidden=!row.dataset.search.toLocaleLowerCase().includes(query) || (status.value==='completed' && row.dataset.status!=='completed') || (status.value==='active' && row.dataset.status==='completed');
      if(!row.hidden)visible++;
      if(row.querySelector('input').checked){selected++;if(row.hidden)hiddenSelected++;}
    });
    document.getElementById('selection-count').textContent=`${selected} selected · ${visible} visible${hiddenSelected ? ` · ${hiddenSelected} selected outside this filter` : ''}`;
    form.querySelectorAll('button[type=submit]').forEach(button=>button.disabled=!selected);
  };
  document.querySelector('[data-selection-tools]').hidden=false;
  search.addEventListener('input',update);status.addEventListener('change',update);form.addEventListener('change',update);
  document.getElementById('select-visible').addEventListener('click',()=>{rows.filter(row=>!row.hidden).forEach(row=>row.querySelector('input').checked=true);update();});
  document.getElementById('clear-selection').addEventListener('click',()=>{rows.forEach(row=>row.querySelector('input').checked=false);update();});
  update();
})();
