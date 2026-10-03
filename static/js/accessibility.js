(function(){
  const warning=document.getElementById("session-warning");
  if(!warning||!window.studentSuccessSessionMinutes)return;
  const warningDelay=Math.max(1000,(window.studentSuccessSessionMinutes-2)*60*1000);
  let timer=window.setTimeout(()=>{warning.hidden=false},warningDelay);
  const title=document.getElementById("session-warning-title");
  const extend=document.getElementById("extend-session");
  const message=document.getElementById("session-warning-message");
  const recovery=document.getElementById("session-recovery");
  extend.addEventListener("click",async()=>{
    extend.disabled=true;
    title.textContent="Checking your session...";
    message.textContent="Reconnecting... This may take a moment while the site wakes up.";
    const controller=new AbortController();
    const timeout=window.setTimeout(()=>controller.abort(),20000);
    try {
      const response=await fetch("/session/extend",{method:"POST",credentials:"same-origin",signal:controller.signal});
      if(response.redirected||response.status===401||response.status===403){
        title.textContent="Your session has ended.";
        message.textContent="Your session has ended. Sign in again to continue. Saved information is still there; unsaved changes on this page may need to be entered again.";
        recovery.hidden=false;
        return;
      }
      if(!response.ok)throw new Error("Session extension failed");
      const result=await response.json();
      if(result.status!=="extended")throw new Error("Unexpected session response");
      warning.hidden=true;
      title.textContent="Your session will expire soon.";
      recovery.hidden=true;
      message.textContent="Extend it to keep working. Saved information will not be deleted.";
      window.clearTimeout(timer);
      timer=window.setTimeout(()=>{warning.hidden=false},warningDelay);
    } catch(error) {
      title.textContent="We could not reconnect.";
      message.textContent="We could not reconnect. The site may still be waking up or your connection may be offline. Try extending again, or sign in again if your session has ended.";
      recovery.hidden=false;
    } finally {
      window.clearTimeout(timeout);
      extend.disabled=false;
    }
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
