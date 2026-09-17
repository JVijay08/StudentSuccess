(() => {
  const dialog = document.getElementById("welcome-dialog");
  const key = "studentsuccess.welcome.v1";
  function acknowledge() { try { localStorage.setItem(key, "seen"); } catch (_) { /* Showing again is safe when storage is blocked. */ } }
  function open() { if (!dialog.open) { dialog.showModal(); document.getElementById("welcome-title").focus(); } }
  // Keep the introduction available on demand without interrupting arrival.
  document.getElementById("welcome-close").addEventListener("click", () => { acknowledge(); dialog.close(); });
  dialog.addEventListener("cancel", acknowledge);
  dialog.addEventListener("close", acknowledge);
  dialog.querySelectorAll("[data-welcome-choice]").forEach(el => el.addEventListener(el.tagName === "FORM" ? "submit" : "click", acknowledge));
  document.getElementById("welcome-reopen").addEventListener("click", open);
})();
