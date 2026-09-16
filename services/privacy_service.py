CONFIRMATION_ERROR = (
    "Confirm that these entries contain no personal or identifying information before continuing. "
    "Use fictional details; remove real names, school names, contact details, and student IDs."
)


def confirmation_errors(form):
    return [] if form.get("nonpersonal_confirmed") == "yes" else [CONFIRMATION_ERROR]
