# StudentSuccess — current project handoff

Copy the text below into Copilot. This describes the implemented application, not an aspirational feature list. Updated October 3, 2026. Read the actual code before proposing changes; older feedback documents and screenshots may describe previous versions.

---

You are helping me develop **StudentSuccess**, an independent academic planner for high-school, dual-enrollment, and college students. Its tagline is **“Plan less. Start sooner.”** The purpose is to connect course planning with day-to-day assignments, give students a clear next action, and help them build realistic study habits without judging their ability or grades.

## Project and deployment

- Live application: https://studentsuccess.onrender.com/
- Main source repository: https://github.com/JVijay08/StudentSuccess
- Separate visual showcase: https://github.com/JVijay08/StudentSuccess-showcase
- Stack: Python, Flask, Jinja templates, Flask-SQLAlchemy, PostgreSQL on Render, SQLite for local development/tests, and vanilla JavaScript/CSS. This is not a React, Next.js, or Sites application.
- Render runs Gunicorn. The main branch deploys automatically. `render.yaml` describes deployment; `app.py` contains the app factory, security headers, error handlers, and additive startup migrations.
- Important server environment variables: `SECRET_KEY`, `DATABASE_URL`, `APP_ENV=production`, `DEMO_RESET_ON_DEPLOY=0`, `PUBLIC_SITE_URL`, `GROQ_API_KEY` (legacy fallback `API_KEY`), optional `GROQ_MODEL`, and `AI_ENABLED`. Never put their secret values in templates, JavaScript, prompts, documentation, screenshots, or logs. A Google site-verification token is public verification metadata, not an API secret.
- Keep production data intact. Use disposable SQLite databases and synthetic records for tests, tutorials, screenshots, and audits. Never reset the hosted database to test a feature.

## Design philosophy and current interface

Preserve the established cream graph-paper background, blue/navy text and controls, restrained gold accents, layered paper/card surfaces, readable typography, and purposeful subtle animation. The user likes this aesthetic and does not want another generic flat dashboard or excessive cards, badges, labels, or duplicate actions.

The recent cleanup reduced oversized headings, simplified task cards, moved secondary details into accessible native disclosures, grouped settings, and tightened mobile layouts. Keep one obvious primary action for each context. Use small menus/disclosures for rescheduling, optional timing, explanations, and advanced settings. Do not hide essential actions or required fields.

The application has light, dark, and high-contrast themes; text/spacing preferences; reduced motion; keyboard navigation; and responsive layouts. Preserve all of these. Avoid animation that steals focus or delays completing a task.

## Accounts and onboarding

- Current sign-in uses a nickname-style **username and password**. It does not collect email, full name, or student ID at signup. Passwords are hashed server-side.
- Old private-code and email login interfaces were retired. A one-time legacy transfer route still exists to preserve existing planners. Do not reintroduce competing login methods.
- There is currently **no email password reset**. State that clearly rather than implying a recovery service exists.
- New accounts must complete onboarding before using the workspace. Logging out and back in cannot bypass it. Onboarding sets education context, timezone, study budget, and planning/display preferences.
- Signup now requires one age-13+/terms acknowledgment. `AccountAgreement` records only its version and timestamp, linked to the account; no birth date or ID is collected. This is not verified age or verified parental consent.
- Actual courses and ordinary real-life tasks are welcome. Do not label persistent accounts as fictional. Ask users to leave out personal identifiers, credentials, private records, and other people's personal information.
- Redundant personal-information checkboxes were removed from routine task/course/onboarding forms. Explicit review remains for imports, and explicit sharing consent remains for AI.

## Tasks and scheduling

- Today highlights the recommended task and a small next-up queue. Full dashboard exposes broader progress and workload information without making it the default focus.
- Tasks can be searched, filtered, sorted, or grouped by course. Completed tasks have their own section.
- Parent assignments have detail pages. Subtasks link back to their parent; both parent and child navigation must remain usable.
- Students can add subtasks manually, split large assignments into work blocks, reuse a task, and select multiple tasks for reviewed bulk deletion.
- Time estimates support up to **10,080 minutes**. Actual minutes are optional at completion; a giant actual-time input should not dominate the current task card.
- Rescheduling lives in the task's three-dot menu. Planned start and deadline are different fields. Existing timezone-aware shortcuts and schedule undo should remain intact.
- Recurrence supports daily, weekly, every-two-week, and monthly schedules. The repeat end date is inclusive. Each occurrence uses the user's selected due time, or 11:59 PM by default, and can be edited independently. Do not treat the repeat-through date as the only occurrence's deadline.
- Progress includes completion history, start-delay summaries/graphs, and estimate accuracy. Early starts count as on time rather than canceling late starts in an average.

## Explainable ranking, separate from AI

Task ordering is deterministic. Active leaf tasks are sorted by:

1. In progress.
2. Overdue deadline.
3. Missed planned start.
4. Due within 24 hours.
5. Upcoming.

Within a tier, higher scores come first, followed by deadline, planned start, and stable task identifiers. Tiers override scores. The known tradeoff is that a recently missed planned start can outrank a task due within 24 hours. This is documented for student testing, not silently changed.

Base score contributions: not started +2; deadline overdue +4, within 24 hours +3, within 48 hours +2, or within a week +1; estimated effort at least 120 minutes +2 or at least 60 minutes +1; high challenge +1; low interest +1. The recommendation layer can incorporate sufficient recorded start history. Inspect the actual services for history thresholds and adjustments instead of inventing a formula.

Sources of truth: `services/task_policy.py`, `services/procrastination_service.py`, `services/suggestion_service.py`, `services/recommendation_explanations.py`, and `docs/ranking-policy-review.md`. Preserve agreement between displayed explanations and the values used to rank tasks. Do not claim this ranking is AI or a prediction of a student's ability.

## Course and college personalization

- High-school planning includes course references, comparisons of up to three courses, and a four-year plan by grade.
- Dual enrollment is integrated directly into the high-school courses page. It is not a separate top-level tab.
- College planning uses terms, credits, requirement categories, program/term preferences, and workload estimates instead of high-school grade structure.
- Students may take courses at multiple institutions. Each college course can have its own institution; selecting a default college must not overwrite existing courses' institutions.
- The bundled IPEDS 2024 directory contains 5,994 institutions searchable by name/state. It is not a complete database of every college's courses.
- Course catalogs combine national/AP/IB references and selected state/local sources. Coverage varies, and some entries are held back pending verification. Do not claim complete statewide course coverage or verified transfer/admissions eligibility.
- The owner may supply custom institution/course databases in the future; they have not supplied those future databases yet.

## AI implemented today

- Server-side Groq integration provides optional assignment planning. Default model: `openai/gpt-oss-20b`, configurable through `GROQ_MODEL`.
- Flow A: break an existing eligible unstarted assignment into suggested steps.
- Flow B: `/tasks/ai/new` takes assignment instructions, a deadline, optional subject, and a minute budget, then presents an editable assignment/steps draft.
- Only the reviewed assignment text and minute budget are sent to Groq. The whole account/profile/course database is not sent. The AI does not operate tools or autonomously modify the planner.
- Consent is required before generation. Drafts must be reviewed and explicitly applied; users can edit/select steps or discard them. Existing-task drafts have stale-state protection and apply-once safeguards.
- Drafts expire after 30 minutes; expired records are cleaned during later requests. Discarding removes the draft. Applying saves only approved tasks/steps and clears preview steps.
- Limits are five requests per user per day, one per minute, and 100 per site per day. Requests are bounded in duration/size; responses are validated. Manual planning still works without an API key or when AI is unavailable.
- AI is not enabled for public tutorial practice accounts. Do not advertise AI as already providing counseling, accurate admissions predictions, scheduling autonomy, or assignment answers.
- Relevant files: `routes/ai_routes.py`, `services/ai_planning.py`, `models/ai_planning.py`, `templates/ai_*.html`, and `docs/ai-planning.md`.

## Tutorial, browser planner, and Calendar

- The prominent trial experience is an interactive **tutorial**, not an abandoned demo page. It creates a separate synthetic practice workspace and demonstrates actual controls across the site. Finishing deletes practice data and preserves/returns to any original account.
- `/planner` is a separate browser-only planner using localStorage. It does not automatically sync to the server account. It has its own export/restore/erase behavior.
- Google Calendar integration currently creates a prefilled deadline event for the user to review and save. Active deadlines can also be exported to ICS; calendar-file imports have a review step.
- These are manual copies, **not OAuth or automatic two-way sync**. Editing/deleting a task does not edit/delete an external Calendar copy.

## Privacy, accessibility, and public pages

- Public notices: `/privacy`, `/terms-of-service`, `/cookies`, `/data-deletion`, `/accessibility`. Shared footer links make them discoverable, including before login and during onboarding.
- Operator location is **Georgia, United States**. The owner explicitly requested a placeholder contact for now. `privacy@example.com` is labeled inactive, with no pretend working email/request workflow.
- Signed-in users can export data, clear completed history, or delete their account using their password. Deletion clears associated planner records, AI drafts, signup acknowledgment, and per-user AI counters. Off-account deletion/support is an acknowledged limitation until a monitored contact exists.
- No advertising, analytics, or third-party tracking SDKs were found. Necessary session storage and requested browser-local functionality are documented. No unnecessary cookie-consent banner was added.
- Third-party services: Render hosting/database, Groq only for requested AI, Google only when Calendar links are opened, and ordinary external links. No frontend AI SDK or public secret is needed.
- Notices do not claim full legal or accessibility certification. Backup/log retention and a real privacy contact need owner configuration before wider release.
- The last release passed 398 Python tests, 35 responsive workspace checks, and automated accessibility rules on 15 pages across three themes. Automated checks are bounded evidence, not proof that every assistive technology works.

## Existing discovery and reliability features

Public homepage, Features/FAQ, and Updates already have unique titles, descriptions, canonicals, Open Graph/Twitter metadata, and a branded social image. `/sitemap.xml` and `/robots.txt` already exist. Private/auth/export routes are noindex and require actual access controls; robots rules are not security. An SVG favicon and custom 400/404/500 pages exist. Recheck these before adding duplicates.

There is existing browser and server form validation, account-attempt throttling, AI quotas, CSRF protection on sensitive flows, and secure production cookie settings. Audit specific gaps rather than assuming these mechanisms cover every route. Render's HTTPS behavior should be verified at the live edge before adding proxy-dependent redirects that might loop.

## How to work on this repository

- Read current code and relevant docs, not just old screenshots or feedback notes. Keep functioning features; finish genuinely incomplete ones instead of duplicating them.
- Preserve the notebook aesthetic and prioritize clarity, real usability, and honest explanations over visual gimmicks or more settings.
- Do not invent student feedback, analytics, usage counts, college data coverage, academic accuracy, security guarantees, or legal compliance.
- Do not add third-party trackers, expose secrets, or export private planner data to AI by default.
- Use meaningful tests for changed behavior; run relevant browser checks at narrow mobile widths and across supported themes.
- Documentation lives in `docs/`; tests in `tests/`; browser checks in `scripts/check_*.py`. Local `.test-*`, `instance` databases, credentials, `handoff/`, and `output/` are not release content. Do not commit local test accounts or unrelated artifacts.
- The current follow-up is a launch-readiness audit: frontend secrets, HTTPS, search/social metadata, icons, sitemap/robots, alternatives for images, asset size, real loading performance, responsive layouts, errors, broken links, form validation, spam prevention, and a clear public call to action. Check what exists, fix verified gaps, and record actual results without claiming every item required new code.
