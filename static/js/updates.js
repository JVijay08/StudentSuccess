(() => {
 const search=document.querySelector('.update-search');if(!search)return;
 const query=document.getElementById('update-query'),category=document.getElementById('update-category');
 const entries=[...document.querySelectorAll('.update-entry')];search.hidden=false;
 const filter=()=>{const words=query.value.trim().toLocaleLowerCase().split(/\s+/);let count=0;entries.forEach(entry=>{entry.hidden=!words.every(word=>entry.textContent.toLocaleLowerCase().includes(word))||Boolean(category.value&&entry.dataset.category!==category.value);if(!entry.hidden)count++;});document.getElementById('update-count').textContent=`${count} of ${entries.length} releases`;document.getElementById('no-updates').hidden=count!==0;};
 query.addEventListener('input',filter);category.addEventListener('change',filter);
})();
