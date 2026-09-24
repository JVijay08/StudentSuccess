(() => {
  "use strict";
  const MAX_TASK_MINUTES = Number(document.body.dataset.maxTaskMinutes);
  const KEY = "studentsuccess.local-plan.v1";
  const $ = id => document.getElementById(id);
  const empty = () => ({version: 1, tasks: [], courses: [], budget: null, context:"high_school"});
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
          !validNumber(t.minutes, 1, MAX_TASK_MINUTES) || !Number.isInteger(t.minutes) ||
          !["not_started", "in_progress", "completed"].includes(t.status)) throw new Error("Invalid task");
      ids.add(t.id);
      if ((t.challenge !== undefined && !["low","medium","high"].includes(t.challenge)) ||
          (t.interest !== undefined && !["low","medium","high"].includes(t.interest))) throw new Error("Invalid task rating");
      return {id:t.id, title:t.title, subject:t.subject, due:t.due, planned:t.planned, minutes:t.minutes,
        started:t.started, completed:t.completed, status:t.status, parent:t.parent || null, actual:t.actual ?? null, challenge:t.challenge || "medium", interest:t.interest || "medium"};
    });
    for (const t of tasks) {
      if (t.parent && (!tasks.some(p => p.id === t.parent && !p.parent) || t.parent === t.id)) throw new Error("Invalid parent");
      if (t.actual !== null && (!Number.isInteger(t.actual) || !validNumber(t.actual,1,MAX_TASK_MINUTES))) throw new Error("Invalid actual duration");
    }
    const courses = data.courses.map(c => {
      if (!c || !validText(c.id, 100) || !c.id || ids.has(c.id) || !validText(c.title, 2000) || !c.title.trim() ||
          !validNumber(c.hours, 0, 168)) throw new Error("Invalid course");
      if ((c.year !== undefined && ![9,10,11,12].includes(c.year)) ||
          (c.catalog !== undefined && !validText(c.catalog,80)) ||
          (c.courseId !== undefined && !validText(c.courseId,200)) ||
          (c.depth !== undefined && !validText(c.depth,80)) ||
          (c.workload !== undefined && !["Low","Medium","High"].includes(c.workload))) throw new Error("Invalid course details");
      ids.add(c.id);
      if (c.term !== undefined && !validText(c.term,60)) throw new Error("Invalid term");
      return {id:c.id, title:c.title, hours:c.hours, term:c.term || "Unassigned term", year:c.year || 9, catalog:c.catalog || "", courseId:c.courseId || "", depth:c.depth || "Not rated", workload:c.workload || "Medium"};
    });
    return {version:1, tasks, courses, budget:data.budget, context:data.context === "college" ? "college" : "high_school"};
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
    const tier = task.status === "in_progress" ? 0 : hours < 0 ? 1 : task.planned && Date.parse(task.planned) <= now ? 2 : hours <= 24 ? 3 : 4;
    return tier * 100 - score;
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
    const next = copy(); Object.assign(next.tasks.find(t => t.id === id), changes);
    syncProjects(next);
    if (commit(next)) {
      $("task-action-status").textContent = changes.status === "completed" ? "Task completed. Open Completed tasks to find or reopen it." : "Task updated.";
      focusTask(id);
    }
  }
  function focusTask(id) {
    const target = document.getElementById('browser-task-' + id) || $("tasks-heading");
    target.focus();
    target.scrollIntoView({block:"center", behavior:"instant"});
  }
  function resetForm() {
    editing = null; $("task-form").reset(); $("save-task").textContent = "Add task";
    $("task-form-heading").textContent = "Plan a task"; $("cancel-edit").hidden = true;
  }
  function editTask(t) {
    editing = t.id;
    $("task-title").value = t.title; $("task-subject").value = t.subject;
    $("task-due").value = localInput(t.due).slice(0,10); $("task-due-time").value = localInput(t.due).slice(11); $("task-parent").value = t.parent || ""; $("local-more").open = true; $("task-start").value = localInput(t.planned);
    $("task-minutes").value = t.minutes; $("save-task").textContent = "Save task";
    $("task-challenge").value = t.challenge; $("task-interest").value = t.interest;
    $("task-form").querySelector("[name=nonpersonal_confirmed]").checked = false;
    $("task-form-heading").textContent = "Edit task"; $("cancel-edit").hidden = false; $("task-title").focus();
  }
  function syncProjects(next) {
    for(const parent of next.tasks) {
      const children = next.tasks.filter(t => t.parent === parent.id);
      if(!children.length) continue;
      parent.status = children.every(t=>t.status === "completed") ? "completed" : children.some(t=>t.started) ? "in_progress" : "not_started";
      parent.completed = parent.status === "completed" ? children.map(t=>t.completed).sort().at(-1) : null;
      parent.actual = parent.status === "completed" ? children.reduce((n,t)=>n+(t.actual||0),0) : null;
      if(!parent.actual || parent.actual > MAX_TASK_MINUTES) parent.actual = null;
    }
  }

  function renderTiming() {
    const rows=state.tasks.filter(t=>t.status === "completed" && !state.tasks.some(c=>c.parent === t.id));
    const timed=rows.filter(t=>t.started && t.planned).sort((a,b)=>Date.parse(a.completed)-Date.parse(b.completed));
    const values=timed.map(t=>(Date.parse(t.started)-Date.parse(t.planned))/60000).sort((a,b)=>a-b);
    const box=$("local-timing-content");box.replaceChildren();
    const label=n=>n===0 ? "On time" : `${Math.abs(n)>=60 ? (Math.abs(n)/60).toFixed(1)+" hr" : Math.abs(n).toFixed(0)+" min"} ${n<0 ? "early" : "late"}`;
    const metrics=node("dl", ""); metrics.className="timing-metrics";
    const onTime=values.filter(v=>v<=0).length;
    const average=values.length ? values.reduce((sum,v)=>sum+Math.max(0,v),0)/values.length : null;
    for(const [title,value] of [["On-time starts",values.length ? Math.round(onTime/values.length*100)+"%" : "No data yet"],["Average lateness",average === null ? "No data yet" : label(average)],["Starts recorded",String(values.length)]]) {
      const item=node("div", "");item.append(node("dt",title),node("dd",value));metrics.append(item);
    }
    box.append(metrics,node("p","Early starts count as on time and never cancel out late starts in average lateness."));
    const detail=node("details", "");detail.append(node("summary","Timing graphs and history"));box.append(detail);
    if(timed.length<2) detail.append(node("p","Complete a few tasks with planned and actual starts to see a pattern."));
    else {
      const scale=Math.max(1,...values.map(Math.abs));
      detail.append(node("h3","Start delay over time"));
      function bar(title,value){const row=node("div","");row.className="chart-row";const track=node("div","");track.className="delay-track";track.setAttribute("aria-hidden","true");const fill=node("i","");const width=Math.abs(value)/scale*48;fill.style.width=width+"%";fill.style.left=(value<0 ? 50-width : 50)+"%";track.append(fill);row.append(node("span",title),track,node("span",label(value)));detail.append(row);}
      timed.slice(-20).forEach(t=>bar(t.title,(Date.parse(t.started)-Date.parse(t.planned))/60000));
      detail.append(node("h3","Start delay by subject"));const groups=new Map();timed.forEach(t=>{const key=t.subject.trim().toLowerCase()||"No subject";groups.set(key,[...(groups.get(key)||[]),(Date.parse(t.started)-Date.parse(t.planned))/60000]);});
      for(const [subject,delays] of groups) if(delays.length>=2) bar(subject,delays.reduce((a,b)=>a+b,0)/delays.length);
    }
    detail.append(node("h3","Estimated vs. actual duration"));const measured=rows.filter(t=>t.actual);if(measured.length<2)detail.append(node("p","Complete two tasks with actual minutes to compare estimates."));
    else {const max=Math.max(...measured.map(t=>Math.max(t.minutes,t.actual)));for(const t of measured.slice(-20)){const row=node("div","");row.className="chart-row";const bars=node("div","");bars.className="duration-track";bars.setAttribute("aria-hidden","true");for(const [value,cls] of [[t.minutes,""],[t.actual,"actual"]]){const i=node("i","");i.className=cls;i.style.width=(value/max*100)+"%";bars.append(i);}row.append(node("span",t.title),bars,node("span",`Estimated ${t.minutes} min; actual ${t.actual} min`));detail.append(row);}}
  }

  function render() {
    const now = Date.now();
    const parentValue = $("task-parent").value;
    $("task-parent").replaceChildren(node("option", "None")); $("task-parent").firstChild.value="";
    for(const p of state.tasks.filter(t=>!t.parent)) {const opt=node("option",p.title);opt.value=p.id;$("task-parent").append(opt);}
    $("task-parent").value=parentValue;
    $("local-subjects").replaceChildren(...[...new Set(["Math","Science","English",...state.courses.map(c=>c.title.slice(0,80)),...state.tasks.map(t=>t.subject)])].filter(Boolean).map(value=>{const o=node("option",value);o.value=value;return o;}));
    renderTiming();
    const active = state.tasks.filter(t => t.status !== "completed").sort((a,b) => rank(a,now)-rank(b,now) || Date.parse(a.due)-Date.parse(b.due) || a.id.localeCompare(b.id));
    const completed = state.tasks.filter(t => t.status === "completed").sort((a,b) => Date.parse(b.completed)-Date.parse(a.completed) || a.id.localeCompare(b.id));
    $("next-heading").textContent = active[0]?.title || (state.tasks.length ? "All caught up." : "Add a task to find your next step.");
    $("next-reason").textContent = active[0] ? reason(active[0], now) : "Start with a deadline and a small estimate of the time you need.";
    $("progress").textContent = `${active.length} active · ${completed.length} completed`;
    const nextTask = active.find(t => !state.tasks.some(c => c.parent === t.id));
    $("next-heading").textContent = nextTask ? nextTask.title : "All caught up.";
    $("next-reason").textContent = nextTask ? reason(nextTask, now) : "Add a task to begin.";
    $("next-actions").replaceChildren(action(
      nextTask ? (nextTask.status === "not_started" ? "Start this task" : "View task in progress") : "Add a task",
      () => {
        if (!nextTask) { resetForm(); $("task-title").focus(); }
        else if (nextTask.status === "not_started") changeTask(nextTask.id, {status:"in_progress", started:new Date().toISOString()});
        else focusTask(nextTask.id);
      }
    ));
    $("next-actions").querySelector("button")?.classList.remove("secondary");
    $("completion-summary").textContent = state.tasks.length ? `${Math.round(completed.length/state.tasks.length*100)}% completed` : "No tasks yet";
    const started = state.tasks.filter(t => t.started && t.planned);
    $("delay-summary").textContent = started.length ? `${Math.round(started.filter(t=>Date.parse(t.started)<=Date.parse(t.planned)).length/started.length*100)}% of recorded starts were on time. Early starts count as on time.` : "Start tasks to compare actual and planned start times.";
    $("start-history").replaceChildren(...state.tasks.filter(t => t.started).sort((a,b) => Date.parse(b.started)-Date.parse(a.started)).slice(0,5).map(t => node("li", `${t.title} · ${format(t.started)}`)));
    const list = $("tasks"); list.replaceChildren();
    const mode = $("local-sort").value;
    if (mode !== "recommended") active.sort((a,b) => (mode === "due" ? Date.parse(a.due)-Date.parse(b.due) : mode === "planned" ? (Date.parse(a.planned)||Infinity)-(Date.parse(b.planned)||Infinity) : String(a[mode]||"").trim().toLowerCase().localeCompare(String(b[mode]||"").trim().toLowerCase())) || a.id.localeCompare(b.id));
    $("completed-list").replaceChildren();
    const visible = [...active, ...completed];
    if (!visible.length) list.append(node("li", "No tasks here yet. Add one when you’re ready."));
    for (const t of visible) {
      const li = document.createElement("li"); li.id = 'browser-task-' + t.id; li.tabIndex = -1; li.append(node("h3", t.title));
      li.append(node("p", `${t.subject ? t.subject + " · " : ""}Due ${format(t.due)} · ${t.minutes} min`));
      if (t.planned) li.append(node("p", `Planned start: ${format(t.planned)}`));
      li.append(node("p", t.status === "completed" ? "Completed" : reason(t, now)));
      if (t.started && t.planned) {
        const delay = Math.round((Date.parse(t.started)-Date.parse(t.planned))/60000);
        li.append(node("p", `Started ${Math.abs(delay)} minutes ${delay < 0 ? "early" : "after the planned start"}.`));
      }
      const children = state.tasks.filter(c => c.parent === t.id);
      if (t.parent) li.prepend(node("p", "Part of " + (state.tasks.find(p => p.id === t.parent)?.title || "assignment")));
      if (children.length) {const progress = node("progress", ""); progress.max=children.length; progress.value=children.filter(c=>c.status === "completed").length; li.append(node("p", `${progress.value} / ${children.length} subtasks completed`), progress);}
      const buttons = document.createElement("div"); buttons.className = "actions";
      if (t.status === "not_started" && !children.length) buttons.append(action("Start", () => changeTask(t.id, {status:"in_progress", started:new Date().toISOString()})));
      if (t.status !== "completed" && !children.length) buttons.append(action("Complete", () => {
        const value = prompt(`Actual minutes spent (1-${MAX_TASK_MINUTES})`, String(t.minutes)); if(value === null) return;
        const actual = Number(value); if(!Number.isInteger(actual) || actual < 1 || actual > MAX_TASK_MINUTES) {tell(`Enter actual minutes from 1 to ${MAX_TASK_MINUTES}.`);return;}
        changeTask(t.id,{status:"completed",actual,started:t.started || new Date().toISOString(),completed:new Date().toISOString()});
      }));
      else if (t.status === "completed" && !children.length) buttons.append(action("Reopen", () => changeTask(t.id, {status:t.started ? "in_progress" : "not_started", completed:null,actual:null})));
      if (!t.parent && !children.length && t.status === "not_started" && t.minutes > 25) buttons.append(action("Create work blocks", () => {
        const next=copy();let remaining=t.minutes,index=1;
        while(remaining>0){const minutes=Math.min(25,remaining);next.tasks.push({id:uid(),title:`Work block ${index++}`,subject:t.subject,parent:t.id,due:t.due,planned:null,minutes,status:"not_started",started:null,completed:null,challenge:t.challenge,interest:t.interest});remaining-=minutes;}
        commit(next);
      }));
      buttons.append(action("Edit", () => editTask(t)));
      buttons.append(action("Delete", () => {
        if(children.length) {tell("Remove subtasks individually before deleting the project."); return;}
        if (!confirm(`Delete “${t.title}”?`)) return;
        const next = copy(); next.tasks = next.tasks.filter(item => item.id !== t.id);
        syncProjects(next);
        if (commit(next) && editing === t.id) resetForm();
      }, "danger"));
      const primaryLabel = t.status === "in_progress" ? "Complete" : "Start";
      [...buttons.children].find(button=>button.textContent===primaryLabel)?.classList.remove("secondary");
      const options=node("details", "");options.append(node("summary","Task actions"));
      for(const button of [...buttons.children]) if(["Edit","Delete","Break into 25-minute blocks"].includes(button.textContent)) options.append(button);
      if(options.children.length>1) buttons.append(options);
      li.append(buttons); (t.status === "completed" ? $("completed-list") : list).append(li);
    }
    if ($("local-view").value === "courses") {
      const key = text => (text || "Unassigned").trim().replace(/\s+/g," ").toLowerCase();
      const nodes = new Map(active.map(t => [t.id, $("browser-task-"+t.id)]));
      const groups = new Map(state.courses.map(c => [key(c.title.slice(0,80)), {name:c.title.slice(0,80), tasks:[]} ]));
      for (const task of active.filter(t => !t.parent)) {
        const name = task.subject.trim() || "Unassigned";
        if (!groups.has(key(name))) groups.set(key(name), {name, tasks:[]});
        groups.get(key(name)).tasks.push(task);
      }
      list.replaceChildren();
      for (const group of [...groups.values()].sort((a,b)=>a.name.localeCompare(b.name))) {
        const section=node("li", ""); section.className="local-course-group";
        section.append(node("h3", group.name));
        const assignments=node("ul", ""); assignments.className="items";
        for (const task of group.tasks) {
          const entry=nodes.get(task.id); const children=active.filter(t=>t.parent===task.id);
          if (children.length) {
            const detail=node("details", "");detail.open=true;detail.append(node("summary",`Subtasks (${children.length} active)`));
            const branch=node("ul", "");branch.className="items subtask-branch";
            children.forEach(child=>branch.append(nodes.get(child.id)));detail.append(branch);entry.append(detail);
          }
          assignments.append(entry);
        }
        if (!group.tasks.length) assignments.append(node("li", "No active assignments for this course."));
        section.append(assignments,action("Add assignment",()=>{resetForm();$("task-subject").value=group.name === "Unassigned" ? "" : group.name;$("task-title").focus();}));
        list.append(section);
      }
      if (!groups.size) list.append(node("li","Add a course or a task with a subject to start your notebook."));
    }
    const courses = $("courses"); courses.replaceChildren();
    const college = state.context === "college";
    $("local-context").value = state.context;
    $("catalog").hidden = college;
    $("local-catalog-link").hidden = college;
    $("local-plan-link").textContent = college ? "Term plan" : "Four-year plan";
    $("custom-course-year").parentElement.hidden = college;
    $("local-term-label").hidden = !college;
    $("courses-heading").textContent = college ? "Your term plan" : "Your four-year plan";
    for (const year of college ? [...new Set(state.courses.map(c => c.term))].sort() : [9,10,11,12]) {
      const rows = state.courses.filter(c => college ? c.term === year : c.year === year);
      const points = rows.reduce((sum,c) => sum+({Low:1,Medium:2,High:3}[c.workload] || 0),0);
      const highCount = rows.filter(c => c.workload === "High").length;
      const load = rows.length >= 8 || highCount >= 4 || points >= 17 ? "Heavy" : rows.length >= 5 || highCount >= 2 || points >= 8 ? "Moderate" : "Light";
      const hours = rows.reduce((sum,c) => sum+c.hours,0);
      const heading = node("li", ""); heading.append(node("h3", `${college ? "Term" : "Year"} ${year} · ${rows.length} courses · ${load} workload estimate`));
      heading.append(node("p", `${hours} estimated study hours / week` + (state.budget !== null && hours > state.budget ? ` · ${Math.round((hours-state.budget)*10)/10} hours over your availability` : "") + (rows.some(c => c.catalog && !c.hours) ? " · Some catalog courses have no hourly estimate yet." : "")));
      courses.append(heading);
      for (const c of rows) {
      const li = document.createElement("li"); li.append(node("h3", c.title), node("p", c.catalog && !c.hours ? "Study hours not estimated yet" : `${c.hours} study hours / week`));
      li.append(node("p", `${c.depth} academic depth · ${c.workload} time commitment`));
      const yearLabel = node("label", "Move to planning year"); const yearSelect = document.createElement("select");
      for (const value of [9,10,11,12]) { const option = node("option", String(value)); option.value = String(value); option.selected = value === c.year; yearSelect.append(option); }
      yearSelect.addEventListener("change", () => { const next = copy(); next.courses.find(item => item.id === c.id).year = Number(yearSelect.value); commit(next); });
      yearLabel.append(yearSelect); if (!college) li.append(yearLabel);
      li.append(action("Remove course", () => {
        if (!confirm(`Remove “${c.title}”?`)) return;
        const next = copy(); next.courses = next.courses.filter(item => item.id !== c.id); commit(next);
      })); courses.append(li);
      }
    }
    $("workload").textContent = `Your ${college ? "term" : "four-year"} plan: ${state.courses.length} courses. ` + (state.budget === null ? "Set weekly availability to compare each year's load." : `${state.budget} study hours available each week; compare one planning year at a time.`);
  }

  $("task-form").addEventListener("submit", event => {
    if (event.defaultPrevented) return;
    event.preventDefault();
    const due = new Date($("task-due").value + "T" + ($("task-due-time").value || "23:59")), planned = $("task-start").value ? new Date($("task-start").value) : null;
    if (!Number.isFinite(due.getTime()) || (planned && !Number.isFinite(planned.getTime()))) { tell("Enter valid dates."); return; }
    const next = copy();
    const fields = {parent:$("task-parent").value || null, title:$("task-title").value.trim(), subject:$("task-subject").value.trim(), due:due.toISOString(), planned:planned?.toISOString() || null, minutes:Number($("task-minutes").value), challenge:$("task-challenge").value, interest:$("task-interest").value};
    const taskId = editing || uid();
    if(fields.parent && !editing && state.tasks.find(t=>t.id === fields.parent)?.status === "completed") {tell("Reopen a subtask before adding work to a completed project.");return;}
    if(fields.parent === taskId || (fields.parent && state.tasks.some(c => c.parent === taskId))) {tell("Only one level of subtasks is supported.");return;}
    if (editing) Object.assign(next.tasks.find(t => t.id === editing), fields);
    else next.tasks.push({id:taskId, ...fields, status:"not_started", started:null, completed:null});
    syncProjects(next);
    if (commit(next)) { resetForm(); focusTask(taskId); }
  });
  $("cancel-edit").addEventListener("click", () => { const taskId = editing; resetForm(); focusTask(taskId); });
  $("show-completed").addEventListener("change", () => {$("local-completed").open = $("show-completed").checked;});
  $("local-sort").addEventListener("change", render);
  $("local-view").addEventListener("change", render);
  $("local-context").addEventListener("change", () => {const next=copy();next.context=$("local-context").value;commit(next);});
  $("budget-form").addEventListener("submit", event => {
    event.preventDefault(); const next = copy(); next.budget = Number($("budget").value); commit(next);
  });
  $("course-form").addEventListener("submit", event => {
    if (event.defaultPrevented) return;
    event.preventDefault(); const next = copy(); next.courses.push({id:uid(), title:$("course-title").value.trim(), hours:Number($("course-hours").value), year:Number($("custom-course-year").value), term:$("local-term").value.trim() || "Unassigned term"});
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
  function refreshComparison() {
    $("course-comparison").replaceChildren(...[...compared.values()].map(row => courseCard(row.course,row.catalog,true)));
    $("comparison-status").textContent = `${compared.size} of 3 courses selected.`;
    $("view-comparison").hidden = compared.size === 0;
    $("view-comparison").textContent = `View comparison (${compared.size})`;
    document.querySelectorAll('.compare-choice').forEach(button => {
      const selected = compared.has(button.dataset.courseKey);
      button.textContent = selected ? "Remove from comparison" : "Compare course";
      button.setAttribute('aria-pressed', String(selected));
    });
  }
  function currentCatalog() { return catalogs.find(c => c.id === $("catalog-choice").value); }
  function courseCard(course, catalog, comparison = false) {
    const card = document.createElement("article");
    card.append(node("h3", course.course_name), node("p", `${catalog.label} \u00b7 ${course.subject} \u00b7 ${course.course_type}`));
    card.append(node("p", `${course.rigor_level} academic depth ? ${course.workload_level} time commitment`));
    card.append(node("p", `Planning years: ${(course.grade_levels || []).join(", ")}`));
    card.append(node("p", `Prerequisites: ${(course.prerequisites || []).join(", ") || "None listed"}`));
    card.append(node("p", `Pathways: ${(course.career_clusters || []).join(", ") || "Core pathway"}`));
    card.append(node("p", `Graduation category: ${course.graduation_category || "Verify locally"}`));
    const key = catalog.id + ":" + course.course_id;
    const compareButton = action(compared.has(key) ? "Remove from comparison" : "Compare course", () => {
      if (compared.has(key)) compared.delete(key);
      else {
        if (compared.size >= 3) { cardStatus.textContent = "Compare up to three courses. Remove one selection before adding another."; return; }
        compared.set(key, {course,catalog});
      }
      refreshComparison();
      if (comparison) $("browser-comparison").focus();
      else cardStatus.textContent = compared.has(key) ? "Selected. Use View comparison above the results to review your choices." : "Removed from comparison.";
    });
    compareButton.classList.add('compare-choice');
    compareButton.dataset.courseKey = key;
    compareButton.setAttribute('aria-pressed', String(compared.has(key)));
    card.append(compareButton);
    const cardStatus = node("p", ""); cardStatus.setAttribute('role', 'status');
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
      if (state.courses.some(c => c.catalog === catalog.id && c.courseId === course.course_id && c.year === Number(year.value))) { cardStatus.textContent = "That course is already planned for this year."; viewPlan.hidden = false; return; }
      const next = copy(); next.courses.push({id:uid(), title:course.course_name, hours:Number(hours.value), year:Number(year.value), catalog:catalog.id, courseId:course.course_id, depth:course.rigor_level, workload:course.workload_level});
      if (commit(next)) { cardStatus.textContent = `Added to year ${year.value}. ${$("message").textContent}`; viewPlan.hidden = false; }
      else cardStatus.textContent = $("message").textContent;
    });
    const viewPlan = node('a', 'View my four-year plan'); viewPlan.href = '#course-area'; viewPlan.hidden = true;
    card.append(form, cardStatus, viewPlan); return card;
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
