(() => {
 const form=document.getElementById('workspace-settings');
 if(!form)return;
 const status=document.getElementById('settings-save-status');
 const initial=new URLSearchParams(new FormData(form)).toString();
 let dirty=false, saving=false;
 const update=()=>{dirty=new URLSearchParams(new FormData(form)).toString()!==initial;status.textContent=dirty?'Unsaved changes':'No unsaved changes';document.getElementById('settings-save-bar').classList.toggle('has-changes',dirty);};
 form.addEventListener('input',update);form.addEventListener('change',update);
 window.addEventListener('beforeunload',event=>{if(dirty&&!saving){event.preventDefault();event.returnValue='';}});
 form.addEventListener('submit',()=>{saving=true;status.textContent='Saving settings...';});
 window.addEventListener('pageshow',()=>{saving=false;update();});
 const zone=document.getElementById('timezone-name');
 const choices=new Set([...document.querySelectorAll('#timezone-options option')].map(o=>o.value));
 const validate=()=>zone.setCustomValidity(choices.has(zone.value)?'':'Choose a time zone from the suggestions.');
 zone.addEventListener('input',validate);
 const detect=document.getElementById('detect-timezone');detect.hidden=false;
 detect.addEventListener('click',()=>{const value=Intl.DateTimeFormat().resolvedOptions().timeZone;const feedback=document.getElementById('timezone-feedback');if(choices.has(value)){zone.value=value;validate();update();feedback.textContent=`Selected ${value}. Save settings to apply it.`;}else{feedback.textContent='Your device time zone was not recognized. Choose one from the suggestions.';}});
})();
