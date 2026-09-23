"""Student-facing explanations of existing scores, with no changes to ranking."""
from collections import Counter
from services import delay_service
from services.task_policy import tier


def explain_recommendations(rows, tasks):
    counts = Counter(delay_service.group_key(task) for task in tasks
                     if task.status == "completed" and delay_service.start_delay(task) is not None)
    averages = delay_service.average_start_delay_by_group(tasks)
    for index, row in enumerate(rows):
        # Prefer the largest actual contributions; put deadlines first on a tie.
        factors = sorted(row["factors"], key=lambda f: (-f["points"], f["key"] != "deadline"))
        words = [factor["short"] for factor in factors[:3]]
        row["short_reason"] = ("; ".join(words).capitalize() + ".") if words else "No extra priority signals apply to this task right now."
        task = row["task"]
        state = row.get("tier", tier(task))
        leading = {0: "it is already in progress", 1: "its deadline has passed", 2: "its planned start has passed", 3: "it is due within 24 hours"}.get(state)
        if leading:
            row["short_reason"] = f"Start here because {leading}, and you estimated {task.estimated_minutes} minutes."
        group = delay_service.group_key(row["task"])
        count = counts[group]
        label = "tasks without a subject or type" if group == "ungrouped" else f"{group} tasks"
        if count < delay_service.MINIMUM_SAMPLE:
            row["history_note"] = f"No history adjustment yet: {count} of {delay_service.MINIMUM_SAMPLE} completed {label} have both planned and actual start times recorded."
        elif row["bonus"]:
            avg = averages[group]
            row["history_note"] = f"Your past starts count: across {count} completed {label}, you started {avg:.1f} hours late on average. This adds a small priority nudge (+{row['bonus']})."
        else:
            row["history_note"] = f"History checked: {count} completed {label}. Average start delay is at most one hour, so no extra priority nudge is added."
        row["comparison_note"] = None
        if index + 1 >= len(rows):
            if len(rows) == 1:
                row["comparison_note"] = "This is your only active task, so there is no other task to rank it against."
            continue
        other = rows[index + 1]
        title = other["task"].title
        if row.get("tier") != other.get("tier"):
            row["comparison_note"] = f'It comes before "{title}" because its work-status / urgency tier takes precedence over score.'
            continue
        if row["score"] == other["score"]:
            if delay_service._as_utc(row["task"].due_at) < delay_service._as_utc(other["task"].due_at):
                row["comparison_note"] = f'Tied in priority with "{title}". This comes first because its deadline is earlier.'
            else:
                row["comparison_note"] = f'The same priority and deadline as "{title}". The rules do not favor one over the other; either is a reasonable starting point.'
        else:
            other_points = {factor["key"]: factor["points"] for factor in other["factors"]}
            phrases = {
                "deadline": "its deadline is in a more urgent time window",
                "start": "this task has not been started yet, while the other has",
                "effort": "you estimated more time for this task",
                "challenge": "you rated this task as more challenging",
                "interest": "you rated your interest in this task lower",
                "history": "your recorded start history gives this task a larger priority nudge",
            }
            advantages = [phrases[factor["key"]] for factor in factors
                          if factor["points"] > other_points.get(factor["key"], 0)]
            row["comparison_note"] = f'Compared with "{title}", ' + "; ".join(advantages) + ". Together, these differences give it higher priority."
    return rows
