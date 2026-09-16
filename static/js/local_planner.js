(() => {
  "use strict";
  const KEY = "studentsuccess.local-plan.v1";
  const $ = id => document.getElementById(id);
  const empty = () => ({version: 1, tasks: [], courses: [], budget: null});
  let state = empty(), lastSaved = null, editing = null, readable = true;
  const tell = message => { $("message").textContent = message; };
  const validText = (value, max) => typeof value === "string" && value.length <= max;
  const validDate = value => typeof value === "string" && value.length <= 40 && Number.isFinite(Date.parse(value));
  const validNumber = (value, min, max) => typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;

  function validate(data) {
    if (!data || data.version !== 1 || !Array.isArray(data.tasks) || !Array.isArray(data.courses) ||
        data.tasks.length > 2000 || data.courses.length > 200 ||
        !(data.budget === null || validNumber(data.budget, 0, 168))) throw new Error("Invalid backup");
    const ids = new Set();
    const tasks = data.tasks.map(t => {
      if (!t || !validText(t.id, 100) || !t.id || ids.has(t.id) || !validText(t.title, 160) || !t.title.trim() ||
          !validText(t.subject, 80) || !validDate(t.due) || !(t.planned === null || validDate(t.planned)) ||
          !(t.started === null || validDate(t.started)) || !(t.completed === null || validDate(t.completed)) ||
          !validNumber(t.minutes, 1, 10080) || !Number.isInteger(t.minutes) ||
          !["not_started", "in_progress", "completed"].includes(t.status)) throw new Error("Invalid task");
      ids.add(t.id);
      if ((t.challenge !== undefined && !["low","medium","high"].includes(t.challenge)) ||
          (t.interest !== undefined && !["low","medium","high"].includes(t.interest))) throw new Error("Invalid task rating");
      return {id:t.id, title:t.title, subject:t.subject, due:t.due, planned:t.planned, minutes:t.minutes,
        started:t.started, completed:t.completed, status:t.status, challenge:t.challenge || "medium", interest:t.interest || "medium"};
    });
    const courses = data.courses.map(c => {
      if (!c || !validText(c.id, 100) || !c.id || ids.has(c.id) || !validText(c.title, 2000) || !c.title.trim() ||
          !validNumber(c.hours, 0, 168)) throw new Error("Invalid course");
      if ((c.year !== undefined && ![9,10,11,12].includes(c.year)) ||
          (c.catalog !== undefined && !validText(c.catalog,80)) ||
          (c.courseId !== undefined && !validText(c.courseId,200)) ||
          (c.depth !== undefined && !validText(c.depth,80)) ||
          (c.workload !== undefined && !["Low","Medium","High"].includes(c.workload))) throw new Error("Invalid course details");
      ids.add(c.id);
      return {id:c.id, title:c.title, hours:c.hours, year:c.year || 9, catalog:c.catalog || "", courseId:c.courseId || "", depth:c.depth || "Not rated", workload:c.workload || "Medium"};
    });
    return {version:1, tasks, courses, budget:data.budget};
  }

  function read() {
    try { lastSaved = localStorage.getItem(KEY); }
    catch (_) { readable = false; tell("Browser storage is unavailable. You can plan temporarily and download a backup before leaving."); return; }
    if (lastSaved !== null) {
      try { state = validate(JSON.parse(lastSaved)); }
      catch (_) {
        readable = false;
        tell("The saved plan could not be read. It has not been overwritten. Download the original data below before restoring a valid backup or erasing it.");
      }
    }
  }

  function commit(next) {
    try { next = validate(next); }
    catch (_) { tell("That change could not be saved. Check the values and plan size (up to 2,000 tasks and 200 courses)."); return false; }
    if (readable) {
      try {
        if (localStorage.getItem(KEY) !== lastSaved) {
          tell("This plan changed in another tab. Reload this page before saving to avoid overwriting those changes.");
          return false;
        }
        const raw = JSON.stringify(next);
        localStorage.setItem(KEY, raw);
        lastSaved = raw;
        tell("Saved in this browser.");
      } catch (_) {
        tell("Browser storage could not save this change. Download a backup before leaving; this change is only in memory.");
        $("storage-state").textContent = "Latest changes are only in memory. Download a backup before leaving.";
        state = next; render(); return true;
      }
    } else {
      tell("This change is only in memory. Download a backup before leaving; existing browser data has not been overwritten.");
    }
    state = next;
    if (readable) $("storage-state").textContent = "Saved on this browser; not uploaded to StudentSuccess.";
    render(); return true;
  }

  const copy = () => JSON.parse(JSON.stringify(state));
  const uid = () => crypto.randomUUID();
  const format = value => new Date(value).toLocaleString([], {dateStyle:"medium", timeStyle:"short"});
  function localInput(value) {
    if (!value) return "";
    const d = new Date(value);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0,16);
  }
  function rank(task, now) {
    const hours = (Date.parse(task.due)-now)/3600000;
    let score = task.started ? 0 : 2;
    score += hours < 0 ? 4 : hours <= 24 ? 3 : hours <= 48 ? 2 : hours <= 168 ? 1 : 0;
    score += task.minutes >= 120 ? 2 : task.minutes >= 60 ? 1 : 0;
    score += task.challenge === "high" ? 1 : 0;
    score += task.interest === "low" ? 1 : 0;
    return -score;
  }
  function reason(t, now) {
    const notes = [];
    if (Date.parse(t.due) < now) notes.push("Deadline has passed");
    else if (Date.parse(t.due)-now <= 86400000) notes.push("Due within 24 hours");
    if (t.status === "not_started" && t.planned && Date.parse(t.planned) < now) notes.push("Planned start has passed");
    if (t.status === "in_progress") notes.push("Already in progress");
    if (t.challenge === "high") notes.push("You rated this task as challenging");
    if (t.interest === "low") notes.push("You rated your interest as low");
    if (!notes.length) notes.push("Based on deadline, start status, and estimated time");
    notes.push(`${t.minutes} minute estimate`);
    return notes.join(" · ");
  }
  function node(tag, text) { const el = document.createElement(tag); el.textContent = text; return el; }
  function action(label, handler, style = "secondary") {
    const button = node("button", label); button.type = "button"; button.className = style;
    button.addEventListener("click", handler); return button;
  }
  function changeTask(id, changes) {
    const next = copy(); Object.assign(next.tasks.find(t => t.id === id), changes); commit(next);
  }
  function resetForm() {
    editing = null; $("task-form").reset(); $("save-task").textContent = "Add task";
    $("task-form-heading").textContent = "Plan a task"; $("cancel-edit").hidden = true;
  }
  function editTask(t) {
    editing = t.id;
    $("task-title").value = t.title; $("task-subject").value = t.subject;
    $("task-due").value = localInput(t.due); $("task-start").value = localInput(t.planned);
    $("task-minutes").value = t.minutes; $("save-task").textContent = "Save task";
    $("task-challenge").value = t.challenge; $("task-interest").value = t.interest;
    $("task-form").querySelector("[name=nonpersonal_confirmed]").checked = false;
    $("task-form-heading").textContent = "Edit task"; $("cancel-edit").hidden = false; $("task-title").focus();
  }
  function render() {
    const now = Date.now();
    const active = state.tasks.filter(t => t.status !== "completed").sort((a,b) => rank(a,now)-rank(b,now) || Date.parse(a.due)-Date.parse(b.due));
    const completed = state.tasks.filter(t => t.status === "completed");
    $("next-heading").textContent = active[0]?.title || (state.tasks.length ? "All caught up." : "Add a task to find your next step.");
    $("next-reason").textContent = active[0] ? reason(active[0], now) : "Start with a deadline and a small estimate of the time you need.";
    $("progress").textContent = `${active.length} active · ${completed.length} completed`;
    $("completion-summary").textContent = state.tasks.length ? `${Math.round(completed.length/state.tasks.length*100)}% completed` : "No tasks yet";
    const started = state.tasks.filter(t => t.started && t.planned);
    $("delay-summary").textContent = started.length ? `Average start delay: ${Math.round(started.reduce((sum,t) => sum+(Date.parse(t.started)-Date.parse(t.planned))/60000,0)/started.length)} minutes (negative means early).` : "Start tasks to compare actual and planned start times.";
    $("start-history").replaceChildren(...state.tasks.filter(t => t.started).sort((a,b) => Date.parse(b.started)-Date.parse(a.started)).slice(0,5).map(t => node("li", `${t.title} · ${format(t.started)}`)));
    const list = $("tasks"); list.replaceChildren();
    const visible = $("show-completed").checked ? [...active, ...completed] : active;
    if (!visible.length) list.append(node("li", "No tasks here yet. Add one when you’re ready."));
    for (const t of visible) {
      const li = document.createElement("li"); li.append(node("h3", t.title));
      li.append(node("p", `${t.subject ? t.subject + " · " : ""}Due ${format(t.due)} · ${t.minutes} min`));
      if (t.planned) li.append(node("p", `Planned start: ${format(t.planned)}`));
      li.append(node("p", t.status === "completed" ? "Completed" : reason(t, now)));
      if (t.started && t.planned) {
        const delay = Math.round((Date.parse(t.started)-Date.parse(t.planned))/60000);
        li.append(node("p", `Started ${Math.abs(delay)} minutes ${delay < 0 ? "early" : "after the planned start"}.`));
      }
      const buttons = document.createElement("div"); buttons.className = "actions";
      if (t.status === "not_started") buttons.append(action("Start", () => changeTask(t.id, {status:"in_progress", started:new Date().toISOString()})));
      if (t.status !== "completed") buttons.append(action("Complete", () => changeTask(t.id, {status:"completed", completed:new Date().toISOString()})));
      else buttons.append(action("Reopen", () => changeTask(t.id, {status:t.started ? "in_progress" : "not_started", completed:null})));
      buttons.append(action("Edit", () => editTask(t)));
      buttons.append(action("Delete", () => {
        if (!confirm(`Delete “${t.title}”?`)) return;
        const next = copy(); next.tasks = next.tasks.filter(item => item.id !== t.id);
        if (commit(next) && editing === t.id) resetForm();
      }, "danger")); li.append(buttons); list.append(li);
    }
    const courses = $("courses"); courses.replaceChildren();
    for (const year of [9,10,11,12]) {
      const rows = state.courses.filter(c => c.year === year);
      const points = rows.reduce((sum,c) => sum+({Low:1,Medium:2,High:3}[c.workload] || 0),0);
      const highCount = rows.filter(c => c.workload === "High").length;
      const load = rows.length >= 8 || highCount >= 4 || points >= 17 ? "Heavy" : rows.length >= 5 || highCount >= 2 || points >= 8 ? "Moderate" : "Light";
      const hours = rows.reduce((sum,c) => sum+c.hours,0);
      const heading = node("li", ""); heading.append(node("h3", `Year ${year} · ${rows.length} courses · ${load} workload estimate`));
      heading.append(node("p", `${hours} estimated study hours / week` + (state.budget !== null && hours > state.budget ? ` · ${Math.round((hours-state.budget)*10)/10} hours over your availability` : "") + (rows.some(c => c.catalog && !c.hours) ? " · Some catalog courses have no hourly estimate yet." : "")));
      courses.append(heading);
      for (const c of rows) {
      const li = document.createElement("li"); li.append(node("h3", c.title), node("p", c.catalog && !c.hours ? "Study hours not estimated yet" : `${c.hours} study hours / week`));
      li.append(node("p", `${c.depth} academic depth · ${c.workload} time commitment`));
      const yearLabel = node("label", "Move to planning year"); const yearSelect = document.createElement("select");
      for (const value of [9,10,11,12]) { const option = node("option", String(value)); option.value = String(value); option.selected = value === c.year; yearSelect.append(option); }
      yearSelect.addEventListener("change", () => { const next = copy(); next.courses.find(item => item.id === c.id).year = Number(yearSelect.value); commit(next); });
      yearLabel.append(yearSelect); li.append(yearLabel);
      li.append(action("Remove course", () => {
        if (!confirm(`Remove “${c.title}”?`)) return;
        const next = copy(); next.courses = next.courses.filter(item => item.id !== c.id); commit(next);
      })); courses.append(li);
      }
    }
    $("workload").textContent = `Your four-year plan: ${state.courses.length} courses. ` + (state.budget === null ? "Set weekly availability to compare each year's load." : `${state.budget} study hours available each week; compare one planning year at a time.`);
  }

  $("task-form").addEventListener("submit", event => {
    if (event.defaultPrevented) return;
    event.preventDefault();
    const due = new Date($("task-due").value), planned = $("task-start").value ? new Date($("task-start").value) : null;
    if (!Number.isFinite(due.getTime()) || (planned && !Number.isFinite(planned.getTime()))) { tell("Enter valid dates."); return; }
    const next = copy();
    const fields = {title:$("task-title").value.trim(), subject:$("task-subject").value.trim(), due:due.toISOString(), planned:planned?.toISOString() || null, minutes:Number($("task-minutes").value), challenge:$("task-challenge").value, interest:$("task-interest").value};
    if (editing) Object.assign(next.tasks.find(t => t.id === editing), fields);
    else next.tasks.push({id:uid(), ...fields, status:"not_started", started:null, completed:null});
    if (commit(next)) resetForm();
  });
  $("cancel-edit").addEventListener("click", resetForm);
  $("show-completed").addEventListener("change", render);
  $("budget-form").addEventListener("submit", event => {
    event.preventDefault(); const next = copy(); next.budget = Number($("budget").value); commit(next);
  });
  $("course-form").addEventListener("submit", event => {
    if (event.defaultPrevented) return;
    event.preventDefault(); const next = copy(); next.courses.push({id:uid(), title:$("course-title").value.trim(), hours:Number($("course-hours").value), year:Number($("custom-course-year").value)});
    if (commit(next)) $("course-form").reset();
  });
  function download(raw, name) {
    const url = URL.createObjectURL(new Blob([raw], {type:"application/json"}));
    const link = document.createElement("a"); link.href = url; link.download = name;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $("export").addEventListener("click", () => download(JSON.stringify(state,null,2), "studentsuccess-backup.json"));
  $("import").addEventListener("change", async event => {
    const file = event.target.files[0]; if (!file) return;
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error("Too large");
      const next = validate(JSON.parse(await file.text()));
      if (!confirm("Confirm this backup contains no personal or identifying information. Restoring replaces this browser's plan; download your current plan first if you want to keep it.")) return;
      if (!readable) { tell("Erase the unreadable browser data first, or use a browser with storage enabled, then restore your backup."); return; }
      if (commit(next)) { resetForm(); $("budget").value = state.budget ?? ""; }
    } catch (_) { tell("That file is not a valid StudentSuccess backup (maximum 5 MB). Your plan has not changed."); }
    finally { event.target.value = ""; }
  });
  $("clear").addEventListener("click", () => {
    if (!confirm("Erase all tasks and courses saved by this planner in this browser? This cannot be undone without a backup.")) return;
    try {
      if (readable && localStorage.getItem(KEY) !== lastSaved) { tell("The plan changed in another tab. Reload before erasing it."); return; }
      localStorage.removeItem(KEY); lastSaved = null; readable = true;
    } catch (_) { tell("Browser storage could not be erased. Use your browser's site-data settings."); return; }
    state = empty(); resetForm(); $("budget").value = ""; render();
    $("storage-state").textContent = "Saved on this browser; not uploaded to StudentSuccess.";
    $("original-download")?.remove(); tell("This browser's plan has been erased.");
  });

  let catalogs = [], filteredCourses = [], shownCourses = 36;
  const compared = new Map();
  function currentCatalog() { return catalogs.find(c => c.id === $("catalog-choice").value); }
  function courseCard(course, catalog, comparison = false) {
    const card = document.createElement("article");
    card.append(node("h3", course.course_name), node("p", `${catalog.label} ? ${course.subject} ? ${course.course_type}`));
    card.append(node("p", `${course.rigor_level} academic depth ? ${course.workload_level} time commitment`));
    card.append(node("p", `Planning years: ${(course.grade_levels || []).join(", ")}`));
    card.append(node("p", `Prerequisites: ${(course.prerequisites || []).join(", ") || "None listed"}`));
    card.append(node("p", `Pathways: ${(course.career_clusters || []).join(", ") || "Core pathway"}`));
    card.append(node("p", `Graduation category: ${course.graduation_category || "Verify locally"}`));
    const key = catalog.id + ":" + course.course_id;
    card.append(action(comparison ? "Remove from comparison" : "Compare course", () => {
      if (comparison) compared.delete(key);
      else {
        if (compared.size >= 3 && !compared.has(key)) { tell("Compare up to three courses at a time. Remove one to add another."); return; }
        compared.set(key, {course,catalog});
      }
      $("course-comparison").replaceChildren(...[...compared.values()].map(row => courseCard(row.course,row.catalog,true)));
      if (!comparison) tell("Course added to the comparison below the catalog.");
    }));
    const form = document.createElement("form");
    const yearLabel = node("label", "Add to planning year"); const year = document.createElement("select");
    for (const value of [9,10,11,12]) { const option = node("option",String(value)); option.value = String(value); year.append(option); }
    year.value = String((course.grade_levels || [9])[0] || 9); yearLabel.append(year);
    const hoursLabel = node("label", "Estimated study hours / week (optional)"); const hours = document.createElement("input");
    hours.type = "number"; hours.min = "0"; hours.max = "168"; hours.step = "0.5"; hoursLabel.append(hours);
    const save = node("button", "Add to four-year plan"); save.type = "submit";
    form.append(yearLabel, hoursLabel, save);
    form.addEventListener("submit", event => {
      event.preventDefault();
      if (state.courses.some(c => c.catalog === catalog.id && c.courseId === course.course_id && c.year === Number(year.value))) { tell("That course is already planned for this year."); return; }
      const next = copy(); next.courses.push({id:uid(), title:course.course_name, hours:Number(hours.value), year:Number(year.value), catalog:catalog.id, courseId:course.course_id, depth:course.rigor_level, workload:course.workload_level});
      if (commit(next)) tell("Course added to your four-year plan in this browser.");
    }); card.append(form); return card;
  }
  function showCatalogResults() {
    const catalog = currentCatalog(); if (!catalog) return;
    $("catalog-results").replaceChildren(...filteredCourses.slice(0,shownCourses).map(course => courseCard(course,catalog)));
    $("catalog-count").textContent = `${filteredCourses.length} matches ? showing ${Math.min(shownCourses,filteredCourses.length)}`;
    $("more-courses").hidden = shownCourses >= filteredCourses.length;
  }
  function applyCatalogFilters() {
    const catalog = currentCatalog(); if (!catalog) return;
    const query = $("catalog-search").value.trim().toLowerCase();
    filteredCourses = catalog.courses.filter(course =>
      (!query || [course.course_name,course.subject,...(course.career_clusters || [])].join(" ").toLowerCase().includes(query)) &&
      (!$("catalog-subject").value || course.subject === $("catalog-subject").value) &&
      (!$("catalog-year").value || (course.grade_levels || []).includes(Number($("catalog-year").value))) &&
      (!$("catalog-type").value || course.course_type === $("catalog-type").value) &&
      (!$("catalog-depth").value || course.rigor_level === $("catalog-depth").value) &&
      (!$("catalog-workload").value || course.workload_level === $("catalog-workload").value));
    shownCourses = 36; $("catalog-description").textContent = catalog.description; showCatalogResults();
  }
  function updateCatalogChoices() {
    const catalog = currentCatalog(); if (!catalog) return;
    for (const [id,field] of [["catalog-subject","subject"],["catalog-type","course_type"],["catalog-depth","rigor_level"],["catalog-workload","workload_level"]]) {
      const select = $(id); select.replaceChildren(); const any = node("option", "Any"); any.value = ""; select.append(any);
      [...new Set(catalog.courses.map(c => c[field]))].filter(Boolean).sort().forEach(value => { const option = node("option",value); option.value = value; select.append(option); });
    }
  }
  $("load-catalog").addEventListener("click", async () => {
    $("load-catalog").disabled = true; $("catalog-status").textContent = "Loading the public course catalogs?";
    try {
      const response = await fetch("/planner/catalogs.json", {credentials:"omit"});
      if (!response.ok) throw new Error("Catalog unavailable");
      const data = await response.json(); catalogs = data.catalogs;
      if (!Array.isArray(catalogs) || !catalogs.length) throw new Error("Invalid catalog");
      $("catalog-choice").replaceChildren(...catalogs.map(c => { const option = node("option",c.label); option.value = c.id; return option; }));
      $("catalog-choice").value = "national"; $("catalog-filter").hidden = false;
      $("load-catalog").hidden = true; $("catalog-status").textContent = "Public catalogs loaded. Searches, comparisons, and your plan stay on this device.";
      updateCatalogChoices(); applyCatalogFilters();
    } catch (_) { $("catalog-status").textContent = "Could not load the catalogs. Your saved plan is unaffected. Try again when connected."; $("load-catalog").disabled = false; }
  });
  $("catalog-choice").addEventListener("change", updateCatalogChoices);
  $("catalog-filter").addEventListener("submit", event => { if (event.defaultPrevented) return; event.preventDefault(); applyCatalogFilters(); });
  $("more-courses").addEventListener("click", () => { shownCourses += 36; showCatalogResults(); });

  read();
  if (!readable) {
    $("storage-state").textContent = "Browser saving is unavailable. Changes are only in memory; download a backup before leaving.";
    if (lastSaved !== null) {
      const original = action("Download original unreadable data", () => download(lastSaved, "studentsuccess-original.json"));
      original.id = "original-download"; $("storage").append(original);
    }
  }
  $("budget").value = state.budget ?? ""; render();
  window.addEventListener("storage", event => { if (event.key === KEY || event.key === null) tell("Browser storage changed in another tab. Reload before making more changes."); });

})();
