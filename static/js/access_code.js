(() => {
  const code = document.getElementById("private-code");
  const status = document.getElementById("code-status");
  document.getElementById("copy-code").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(code.value); status.textContent = "Code copied. Save it somewhere private before continuing."; }
    catch (_) { code.focus(); code.select(); status.textContent = "Copy the selected code manually using your device’s copy command."; }
  });
  document.getElementById("download-code").addEventListener("click", () => {
    const content = "StudentSuccess private access code\n\n" + code.value + "\n\nOpen " + location.origin + "/login and paste this code.\nAnyone with this code can access your planner. Keep this file private.\n";
    const url = URL.createObjectURL(new Blob([content], {type:"text/plain"}));
    const link = document.createElement("a"); link.href = url; link.download = "studentsuccess-private-code.txt";
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = "Code file downloaded. Keep it somewhere private.";
  });
})();
