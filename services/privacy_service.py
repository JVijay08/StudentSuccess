CONFIRMATION_ERROR = (
    "Confirm that these entries exclude personal identifiers and sensitive details before continuing. "
    "Your actual courses and tasks are welcome. Leave out full names, student IDs, contact details, "
    "passwords, and private records."
)


def confirmation_errors(form):
    return [] if form.get("nonpersonal_confirmed") == "yes" else [CONFIRMATION_ERROR]
