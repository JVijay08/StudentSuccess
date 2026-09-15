(function () {
  const tour = document.getElementById("demo-checklist");
  const dismiss = document.getElementById("dismiss-demo-checklist");
  if (!tour || !dismiss) return;
  try {
    if (window.localStorage.getItem("studentsuccess-demo-tour-dismissed") === "1") {
      tour.hidden = true;
    }
    dismiss.addEventListener("click", function () {
      tour.hidden = true;
      window.localStorage.setItem("studentsuccess-demo-tour-dismissed", "1");
    });
  } catch (_error) {
    dismiss.addEventListener("click", function () { tour.hidden = true; });
  }
})();
