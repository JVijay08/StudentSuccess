# UI overhaul — September 22, 2026

Implemented in the local working tree. No deployment was performed.

## Applying the supplied design advice

- **Refactoring UI: palette.** One shared neutral scale, blue primary scale, and semantic success/warning/error colors now define the workspace. Removed palette declarations from seven page stylesheets and stopped loading the competing studio, fieldnotes, and depth visual layers. Page styles retain their layout responsibilities; `static/css/overhaul.css` owns the shared visual system. Accessibility preferences load afterward.
- **Refactoring UI: labels.** Assignment titles and metric values carry the strongest emphasis. Subject, duration, and due date support the task title. Timing values appear above smaller descriptive labels. Form labels remain visible; estimated and actual minutes remain distinct.
- **NN/g: hierarchy, scale, grouping.** Reduced oversized interior headings, decorative effects, typography variations, and competing button treatments. Consistent spacing, surfaces, navigation, and readable form controls now connect the dashboard, tasks, courses, comparisons, settings, access screens, and browser planner.
- **GOV.UK: details.** Essential Start and Complete actions stay visible. Calculation details, examples, history, completed work, and transfer tools use disclosure. Task-entry deep links open the form automatically; invalid fields reveal their containing disclosure.
- **Mobbin references.** Applied compact task-first workflows and predictable navigation, while retaining this site's own restrained paper-and-blue identity.

## Changes to the daily workflow

- Shared workspace navigation shows Today, Tasks, Course load, and Profile where appropriate, with active-page indication and academic context. Settings and account actions remain in the existing utility menu.
- The dashboard places a direct Start or Complete action before optional calculation details. Today mode keeps timing/history collapsed. Full dashboard remains available and existing saved preferences remain respected.
- The task queue precedes creation. Add a task opens and scrolls to the form. In-progress tasks show actual minutes and Complete directly, while editing and deleting remain secondary.
- Completed work stays separate. Import/export controls no longer displace the active queue on mobile.
- Removed the duplicate demo tour; retained one dismissible, reopenable guide.
- Simplified the landing page to a single dominant demo action, secondary planner creation, an explicitly fictional product preview, three concrete benefits, and concise storage information.
- Course comparisons, catalog filters, and course plans use the same type and color system. Optional comparison examples collapse, leaving more room for actual course results.
- The browser planner uses the same surfaces and action colors, puts its task list before creation, and collapses timing history.

Existing task ordering, 10,080-minute limits, subtasks, work blocks, college terms, calendar import/export, privacy confirmations, and persistence are preserved.

## Verification

Full regression suite: 282 passed. After the final layout refinements, 55 relevant regression tests also passed. Browser checks exercise local task/subtask persistence, Start/Complete, work-block creation, college terms, dashboard actions, task-entry deep links, and shared stylesheet loading. Responsive checks cover 320, 390, 768, and 1440 pixels across dashboard, tasks, settings, terms, import, browser planner, catalog, course plan, and comparisons. Dark/high-contrast modes, reduced motion, 200% text, and keyboard focus are also checked. A computed-style contrast assertion also verifies the browser planner recommendation text meets 4.5:1. The final Chrome run reported no JavaScript errors or horizontal overflow. Screenshots are generated under `.test-overhaul-browser/`.

This is browser and regression verification, not a claim of a complete assistive-technology audit or a new user-testing study. The fictional landing preview is illustrative rather than an interactive planner.

## Maintaining the system

Use the existing neutral/primary/semantic variables instead of adding page-specific palettes. Keep one principal action per workflow. Use semantic heading levels and real form labels. Put optional explanations in native details elements; keep essential decisions and actions exposed. Preserve accessibility overrides and test reflow whenever a new layout or control is added.

Sources supplied by the user: [palette](https://refactoringui.com/previews/building-your-color-palette/), [labels](https://refactoringui.com/previews/labels-are-a-last-resort/), [visual-design principles](https://www.nngroup.com/articles/principles-visual-design/), [details](https://design-system.service.gov.uk/components/details/), and [Mobbin](https://mobbin.com/).
