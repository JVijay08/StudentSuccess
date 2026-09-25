# StudentSuccess

**Plan less. Start sooner.**

StudentSuccess helps high-school and college students plan a manageable course load and decide which assignment to start next. It brings together four-year course planning, explained task priorities, and feedback on planned versus actual start times.

**[Try the live demo](https://studentsuccess.onrender.com/)** · [Data sources](docs/data_sources.md) · [Privacy notes](docs/privacy_notes.md) · [Architecture](docs/architecture.md) | [Project updates](https://studentsuccess.onrender.com/updates)

> Early release: plan your actual courses and tasks. Leave out full names, student IDs, contact details, passwords, and private records. The demo server may take about a minute to wake after inactivity.

## Take a look

![StudentSuccess landing page](docs/screenshots/landing.png)

![StudentSuccess dashboard with a recommended next task](docs/screenshots/dashboard.png)

[View all eleven screenshots](docs/screenshots/README.md), including the interactive example, tasks, course comparisons, the four-year plan, two-column settings, mobile views, and dark appearance.

## The current workspace

- **College and dual-enrollment planning.** Search 5,994 institutions in the IPEDS 2024 directory by state/name, save a college for either preset, and add college courses alongside high-school courses. Track grade, term, credits and planning status. [Coverage and catalog roadmap](docs/college-planning.md).

- **A dimensional notebook.** Restrained graph paper, layered paper surfaces, raised controls, and purposeful motion, with consistent navigation and readable content.
- **A clearer next action.** The task queue comes first. Start and Complete stay visible; recommendation calculations and timing history expand when needed.
- **Manageable projects.** Organize courses, assignments, and subtasks in the By course view. Split long assignments into timed work blocks, track progress, and keep completed work separate. Estimates support up to 10,080 minutes.
- **Planning for your context.** Compare high-school courses or organize college courses by term. Import assignments from calendar files and review planned versus actual timing.
- **Your preferred pace.** Light, dark, and high-contrast appearances; adjustable text, spacing, and focus; reduced-motion support; and expandable summaries on mobile.

See the [overhaul 2.0 notes](docs/overhaul-2-notebook.md) for implementation and verification details. The screenshot gallery below retains dated captures of earlier releases.

## What you can do

- **Choose what to start next.** See task recommendations with plain-language reasons based on deadlines, estimated effort, task ratings, and available start-history patterns.
- **Turn deadlines into a starting plan.** Set planned start times, start and complete tasks, record actual duration, and review timing and estimation patterns. Recurring tasks and optional in-app reminders support ongoing work.
- **Compare course options.** Try a suggested comparison or select up to three courses. See workload tradeoffs, shared and distinct prerequisites, pathway differences, and grade listings; filter to differences and add a choice directly to your four-year plan.
- **Make the workspace easier to use.** Adjust themes, text size and spacing, reduced motion, focus mode, dashboard density, and visible cards.
- **Keep control of your plan.** Export account data, download a calendar file, clear completed history, or delete your account.

Recommendations use explicit rules. StudentSuccess does not currently use AI or machine learning.

## Try a workspace

| Option | How it works |
| --- | --- |
| **Demo workspace** | Open an isolated workspace with sample tasks and history. A short tour introduces the main features. |
| **Your planner** | Choose a nickname-style username and password, then personalize your planner. No email, full name, or student ID needed. |
| **Browser-only planner** | The existing `/planner` workspace keeps plans on your device. Backups move them manually. |

Save your username and password in a password manager: there is no email reset. Existing private-code planners can be transferred once from the account creation page; transfer replaces the old credential while preserving the plan. Every server account must complete personalization before using the workspace, even after logging out and back in. Browser-only plans remain separate and do not sync automatically.

Free-text submissions welcome actual course and task details and ask you to confirm that personal identifiers and sensitive details are excluded. This is a user acknowledgment, not automatic detection. See the [privacy notes](docs/privacy_notes.md) for storage and account details.

## Course references and limits

The explorer offers state selection for all 50 states, national reference courses, AP and IB catalogs, and selected local course references. Imported state coverage varies; selecting a state does not mean a complete statewide catalog is available. The [data sources](docs/data_sources.md) document coverage and provenance.

Academic depth, workload, and task-priority labels are planning estimates. Confirm current offerings, prerequisites, and graduation requirements with your school counselor. This prototype is not ready to hold real student records.

## Next steps

Priorities include more reliable hosting, stronger public-form protections, clearer connections between planned courses and assignments, and continued usability testing. Adaptive scheduling and optimization remain future work. Calendar-file import and export are available; live calendar synchronization is not implemented.

## License

[MIT](LICENSE)

## Accounts and streamlined planning

Username/password is the sole daily sign-in method. [Account setup](docs/account-setup.md)
explains the onboarding gate, one-time planner transfer, and account limitations.

Tasks offer direct completion, inline rescheduling with timezone-aware shortcuts, and
a ten-minute undo window that preserves newer edits. Rescheduling never changes the
deadline. Actual minutes remain optional; task search stays in the browser. Each course
can belong to a different college in either academic preset.
