(function(){
  const warning=document.getElementById("session-warning");
  if(!warning||!window.studentSuccessSessionMinutes)return;
  const warningDelay=Math.max(1000,(window.studentSuccessSessionMinutes-2)*60*1000);
  let timer=window.setTimeout(()=>{warning.hidden=false;document.getElementById("extend-session").focus()},warningDelay);
  document.getElementById("extend-session").addEventListener("click",async()=>{
    await fetch("/session/extend",{method:"POST",credentials:"same-origin"});
    warning.hidden=true;
    window.clearTimeout(timer);
    timer=window.setTimeout(()=>{warning.hidden=false;document.getElementById("extend-session").focus()},warningDelay);
  });
})();

document.querySelectorAll("[data-password-toggle]").forEach(button=>{
  button.addEventListener("click",()=>{
    const input=document.getElementById(button.dataset.passwordToggle);
    const showing=input.type==="text";
    input.type=showing?"password":"text";
    const label=input.name==="access_code"?"code":"password";
    button.textContent=(showing?"Show ":"Hide ")+label;
    button.setAttribute("aria-pressed",String(!showing));
  });
});
