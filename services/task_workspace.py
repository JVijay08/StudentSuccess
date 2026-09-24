"""A course/subject -> assignment -> subtask view over existing saved tasks.

Grouping uses normalized subject names and never changes recommendation order.
Parents define the assignment's course; completed children count toward progress
but stay out of the active work list.
"""
from services.task_policy import subject_key


def course_outline(tasks, rows, course_names=()):
    groups = {}
    by_id = {row["task"].id: row for row in rows}
    positions = {task_id: index for index, task_id in enumerate(by_id)}
    for name in course_names:
        name = name[:80].strip()
        if name:
            groups.setdefault(subject_key(name), {"name": name, "assignments": [], "active": 0})
    for task in tasks:
        if task.parent_task_id or task.status == "completed":
            continue
        name = task.subject.strip() if task.subject else "Unassigned"
        group = groups.setdefault(subject_key(name), {"name": name, "assignments": [], "active": 0})
        children = sorted((by_id[c.id] for c in task.children if c.id in by_id),
                          key=lambda row: positions[row["task"].id])
        group["assignments"].append({"task": task, "row": by_id.get(task.id), "children": children})
        group["active"] += len(children) if task.children else int(task.id in by_id)
    return sorted(groups.values(), key=lambda group: (group["name"] == "Unassigned", subject_key(group["name"])))
