# Navigation and action flow

Navigation follows the route taken through the workspace. Back links name the
previous page, retain its context, and unwind the trail. Dashboard and home links
remain explicit shortcuts. Direct/bookmarked pages have useful parent defaults.
Settings and Updates live in a small gear menu in the upper-right corner of
authenticated pages, outside the main sidebar links. The menu also offers logout
and supports keyboard activation, Escape, and dismissal by clicking outside.

| Area | Expected action / return |
| --- | --- |
| Dashboard | Course Load opens the plan; task creation opens the form; task planner opens the queue. Start, reschedule, and snooze stay on the dashboard. |
| Four-year plan | Course details return to this plan. Explore opens the catalog. Task planning can return to the plan. Course removal stays on the plan and shows confirmation. |
| Course explorer | Applying filters creates a reloadable search. Details and comparisons retain that search as their parent. Reset clears filters. Quick add can be cancelled and stays on the results after adding. |
| Comparison | Details return to the exact comparison. Change selection restores the explorer's filters and selected course IDs. Adding stays on the comparison; My plan opens the plan. |
| Course details | Back returns to the originating plan, explorer, or comparison. Adding stays on the detail and shows confirmation. Open my plan is an explicit onward action. |
| Tasks | Edit opens the editor. Cancel and Save return to that task in the queue; validation errors preserve the return path. Start, Complete, and Undo stay with the task. Delete returns to the queue. |
| Profile / planning preferences | Editing returns to the originating page when saved. Settings opened from profile returns to profile, including after saving. |
| Settings | Saving and account-maintenance errors stay in settings. Exports download files. Code replacement returns to settings after the new code is saved. Account deletion exits the workspace. |
| Sign-in and creation | Public Back links retain their preceding page. Successful sign-in resumes a requested workspace page. New planner creation continues to the dashboard after the code-saving step. |
| Browser planner | A return link leads back to planner creation or its actual source. Sidebar links move within the browser workspace. Data and actions remain local. |
| Updates | Returns to its originating page; search filters entries in place. |

Return trails are signed, bounded to eight pages, and passed with links/forms,
so one tab does not overwrite another's parent. Only known local GET pages are
allowed as return destinations; referrer headers are never trusted. Downloads,
logout, and mutation endpoints cannot become return destinations. The main
navigation works without JavaScript and does not replay POST requests.

Course search text is kept out of navigation URLs. Up to three recent searches
are held in the signed session, keyed by opaque IDs; expired searches invite the
user to reapply filters. Search confirmation requirements remain in force.

Verification: `tests/test_navigation.py`, the existing route suite,
`scripts/check_navigation.py` (browser clicks, links, tabs, Back), and
`scripts/check_mobile_layout.py --check` (responsive overflow).
