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
      return {id:t.id, title:t.title, subject:t.subject, due:t.due, planned:t.planned, minutes:t.minutes,
        started:t.started, completed:t.completed, status:t.status};
    });
    const courses = data.courses.map(c => {
      if (!c || !validText(c.id, 100) || !c.id || ids.has(c.id) || !validText(c.title, 120) || !c.title.trim() ||
          !validNumber(c.hours, 0, 168)) throw new Error("Invalid course");
      ids.add(c.id);
      return {id:c.id, title:c.title, hours:c.hours};
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
    if (Date.parse(task.due) < now) return 0;
    if (task.status === "not_started" && task.planned && Date.parse(task.planned) < now) return 1;
    return 2;
  }
  function reason(t, now) {
    const notes = [];
    if (Date.parse(t.due) < now) notes.push("Deadline has passed");
    if (t.status === "not_started" && t.planned && Date.parse(t.planned) < now) notes.push("Planned start has passed");
    if (t.status === "in_progress") notes.push("Already in progress");
    if (!notes.length) notes.push("Earliest upcoming deadline");
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
    $("task-form-heading").textContent = "Edit task"; $("cancel-edit").hidden = false; $("task-title").focus();
  }
  function render() {
    const now = Date.now();
    const active = state.tasks.filter(t => t.status !== "completed").sort((a,b) => rank(a,now)-rank(b,now) || Date.parse(a.due)-Date.parse(b.due));
    const completed = state.tasks.filter(t => t.status === "completed");
    $("next-heading").textContent = active[0]?.title || (state.tasks.length ? "All caught up." : "Add a task to find your next step.");
    $("next-reason").textContent = active[0] ? reason(active[0], now) : "Start with a deadline and a small estimate of the time you need.";
    $("progress").textContent = `${active.length} active · ${completed.length} completed`;
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
    for (const c of state.courses) {
      const li = document.createElement("li"); li.append(node("h3", c.title), node("p", `${c.hours} study hours / week`));
      li.append(action("Remove course", () => {
        if (!confirm(`Remove “${c.title}”?`)) return;
        const next = copy(); next.courses = next.courses.filter(item => item.id !== c.id); commit(next);
      })); courses.append(li);
    }
    const total = Math.round(state.courses.reduce((sum,c) => sum+c.hours,0)*10)/10;
    const difference = state.budget === null ? null : Math.round((state.budget-total)*10)/10;
    $("workload").textContent = `${total} estimated study hours / week` + (difference === null ? ". Add your availability to compare." : difference < 0 ? ` · ${-difference} hours over your availability. Consider reducing the load.` : ` · ${difference} hours remaining for other work.`);
  }

  $("task-form").addEventListener("submit", event => {
    event.preventDefault();
    const due = new Date($("task-due").value), planned = $("task-start").value ? new Date($("task-start").value) : null;
    if (!Number.isFinite(due.getTime()) || (planned && !Number.isFinite(planned.getTime()))) { tell("Enter valid dates."); return; }
    const next = copy();
    const fields = {title:$("task-title").value.trim(), subject:$("task-subject").value.trim(), due:due.toISOString(), planned:planned?.toISOString() || null, minutes:Number($("task-minutes").value)};
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
    event.preventDefault(); const next = copy(); next.courses.push({id:uid(), title:$("course-title").value.trim(), hours:Number($("course-hours").value)});
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
      if (!confirm("Replace this browser's plan with this backup? Download your current plan first if you want to keep it.")) return;
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
  setInterval(render, 60000);
})();
