# AI step planning (beta)

Open an unstarted assignment with no subtasks or recurring schedule, then choose
**Suggest steps with AI**. Review the assignment text, consent to sharing it with
Groq, and request a draft. Edit titles/minutes, uncheck unwanted steps, and explicitly
add the selected steps. Discarding does not change the assignment.

The task-entry form also offers **Draft from assignment text with AI**. A rough note or vague study goal can produce a suggested title, subject, deadline, focused-work estimate, and concrete steps/checkpoints. Missing deadlines remain empty for the student to supply. The review screen makes the title, subject, deadline, total estimate, and each step editable. Relative dates and estimates must be checked. Manual deadline/estimate entry remains available. No new database columns are needed.

Review also offers **Spread the work across study sessions**. It uses AI-generated steps and a deterministic local scheduler, not an AI-controlled calendar. Students choose a first study time and daily minute budget. Long steps split into at most eight sessions; the scheduler retains local wall-clock time across days, avoids other uncompleted leaf tasks with planned starts, includes ten-minute breaks, and rejects plans that cannot fit before the deadline. It does not know external calendar events, classes, or unplanned work. Preview writes no tasks; apply validates the dates/conflicts again and requires explicit confirmation. Existing assignments must be unstarted, non-recurring, and have no subtasks; other tasks keep the manual rescheduler.

Recommendation explanations already translate actual ranking factors into readable reasons, comparisons, and recorded-history notes. They remain deterministic, with no AI rewrite that might invent reasons or change the ordering.

AI does not independently change schedules or deadlines, rank tasks, browse websites, verify course requirements, or complete schoolwork. Date suggestions and locally generated study sessions require review. Existing deterministic ranking remains unchanged.

## Render configuration

Set these on the **web service**, directly or through a linked environment group:

| Variable | Value |
| --- | --- |
| GROQ_API_KEY | A newly generated, private Groq API key |
| GROQ_MODEL | Optional; defaults to openai/gpt-oss-20b |
| AI_ENABLED | 1 to enable with a key; 0 to disable |

For compatibility with the initial setup, API_KEY is accepted when GROQ_API_KEY
is absent. GROQ_API_KEY takes precedence. Never commit either value. A key previously
shown in a screenshot must be revoked and replaced. Configuration does not change
DATABASE_URL or SECRET_KEY.

Without a key, the AI page explains that suggestions are unavailable and points back
to manual steps. Tutorial/demo sessions cannot consume provider credits. Start with
Groq's free plan and provider-side limits; the app does not enable billing.

## Boundaries and data handling

Only the text visible in the AI request form and the assignment's minute budget go
to Groq in manual/step mode. Task-detail inference also sends today's local date. Names, account IDs, other tasks, institutions, and study history are not
automatically included. Users can edit the prefilled task title before sending.
The notice is an acknowledgment, not automated personal-data detection.

The provider is called server-side over HTTPS with a 15-second timeout, bounded
output, no tools, and no retries. JSON is validated independently of the model:
1-8 steps, titles up to 160 characters, positive integer minutes, total within the
assignment estimate. Text is escaped by Jinja, never rendered as provider HTML.

Limits are 5 attempts/account/day (UTC), 1/account/minute, and 100/site/day.
Atomic database counters apply across workers and restarts. Provider failures consume
an attempt. Two additive tables, ai_quotas and ai_drafts, are created by normal startup.
No existing tables or data are reset.

Drafts are server-stored and expire after 30 minutes; expired content is removed
on subsequent generation requests. Discard deletes it immediately, apply clears
its text, and account deletion removes associated drafts. Request descriptions
and provider error bodies are not logged or stored by this feature. Groq's own
retention is governed by its settings and terms; do not promise zero retention
unless it is configured there.

Saving requires ownership, CSRF, an unchanged eligible assignment when editing existing work, valid edited
steps, and explicit confirmation. A consumed flag prevents repeat submission.
Subtasks inherit subject, task type, deadline, challenge, interest, and reminders.
They do not receive invented planned start dates.

## Provider terms

The service operator must satisfy Groq's account eligibility requirements.
Do not submit data from children below 13 or the applicable local age of digital
consent. The request form includes the corresponding acknowledgment without asking
for a date of birth. Review provider and model terms for the deployment's audience.

- [Groq models](https://console.groq.com/docs/models)
- [API reference](https://console.groq.com/docs/api-reference)
- [Data handling](https://console.groq.com/docs/your-data)
- [Services agreement](https://console.groq.com/docs/legal/services-agreement)

## Verification

Run tests/test_ai_planning.py and scripts/check_ai_planning.py. Automated tests
stub the provider: no credentials, production accounts, or paid requests are used.
A live provider smoke test is a separate deployment check.
