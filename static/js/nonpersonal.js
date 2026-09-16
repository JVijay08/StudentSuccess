document.querySelectorAll("form[data-nonpersonal-form]").forEach(form => {
  const inputs = [...form.querySelectorAll("[data-nonpersonal-input]")];
  const checkbox = form.querySelector("[name=nonpersonal_confirmed]");
  if (!checkbox) return;
  const values = () => JSON.stringify(inputs.map(input => input.value));
  const needsConfirmation = () => !form.hasAttribute("data-optional-confirmation") || inputs.some(input => input.value.trim());
  let confirmedValues = null;
  // A browser may restore form state on Back. Always ask again for a new submission.
  function reset() { checkbox.checked = false; confirmedValues = null; checkbox.required = needsConfirmation(); }
  reset();
  window.addEventListener("pageshow", reset);
  inputs.forEach(input => {
    input.setAttribute("aria-describedby", [input.getAttribute("aria-describedby"), (form.querySelector("[data-privacy-note]")?.id || "nonpersonal-note")].filter(Boolean).join(" "));
    input.addEventListener("input", reset);
    input.addEventListener("change", reset);
  });
  checkbox.addEventListener("change", () => { confirmedValues = checkbox.checked ? values() : null; });
  form.addEventListener("submit", event => {
    if (needsConfirmation() && (!checkbox.checked || confirmedValues !== values())) {
      event.preventDefault(); reset(); checkbox.reportValidity(); checkbox.focus();
    }
  });
});
