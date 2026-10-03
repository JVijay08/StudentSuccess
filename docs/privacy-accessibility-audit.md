# Privacy and accessibility review — October 3, 2026

## Implemented

- Public privacy, terms, storage, deletion, and accessibility pages; shared footer links. Notices remain available without login and during mandatory onboarding.
- Operator jurisdiction: Georgia, United States. `privacy@example.com` is explicitly inactive, not a working request channel, per the operator's instruction. No misleading mailto link or request form that drops submissions.
- One signup acknowledgment for age 13+ and terms, with version/time stored in `account_agreements`. No birth date, identity document, name, or IP is added to that record. This is an eligibility acknowledgment, **not verified age or parental consent**. It cannot establish COPPA compliance by itself.
- Ordinary course/task forms no longer repeat personal-information checkboxes. Explicit AI provider sharing consent and import review remain. No marketing consent is collected because no marketing flow exists.
- Existing password/CSRF-protected account deletion is linked publicly. Associated records cascade, including AI drafts and acknowledgment; user AI counters are removed. Completed-history deletion now also verifies CSRF.
- Keyboard sort requires an explicit Sort action instead of navigating while a selection changes. Contrast and keyboard checks are recorded by the local audit script.

## Third-party and storage inventory

| Component | Current use | Control |
| --- | --- | --- |
| Render / managed database | Application hosting, account/planner persistence, request metadata | Server configuration; confirm actual logs/backups retention with hosting settings |
| Groq API | Assignment text and minute budget for requested drafts | Server-only API key, bounded requests, per-request sharing acknowledgment; user review before task creation |
| Google Calendar | User-opened add-event links carrying deadline details | Explicit navigation; no OAuth token, SDK, or two-way sync |
| GitHub and policy links | Ordinary external navigation | No embedded trackers |
| Analytics / advertising / social SDKs / external fonts | None found in application assets | Do not introduce without reviewing disclosure and consent needs |
| Session cookie | Authentication, CSRF, navigation/tutorial state | HttpOnly, SameSite=Lax, Secure in production; logout and inactivity handling |
| localStorage | Requested browser-only plan; guide dismissal flags | Erase planner / clear site storage |
| sessionStorage | Short-lived visual action markers | Consumed by action handling; stale after two minutes; per tab |

Axe-core is downloaded into an ignored local test folder for auditing. It is **not** included in the site's dependencies, served assets, or browser production requests.

## Deliberately omitted

- No consent banner for nonexistent optional tracking. The storage policy describes functional storage and how to clear it. Reassess before adding analytics, ads, or optional third-party scripts.
- No date-of-birth collection, ID upload, generic "agree to all data processing" field, or unimplemented parental verification promise.
- No new manual deletion database or pretend email workflow. Signed-in deletion is immediate; off-account support remains an explicitly disclosed limitation.

## Owner follow-up before wider release

Replace the placeholder with a monitored privacy/accessibility contact and identify the actual responsible operator in the notices. Configure and document hosting backup/log retention and a process for requests about lost accounts or children's data. Verify provider settings and review the notices for the actual audience/jurisdictions. Do not treat these pages or an age checkbox as legal certification. Existing accounts have not been retroactively recorded as accepting new terms.

## Sources used

- [FTC COPPA guidance](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions), including the distinction between teen/general-audience services, actual knowledge, and verified parental consent.
- [ICO cookies and privacy notices](https://ico.org.uk/for-organisations/advice-for-small-organisations/privacy-notices-and-cookies/cookies-and-privacy-notices-in-detail/): distinguish strictly necessary storage from optional tracking.
- [W3C contrast minimum](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html): 4.5:1 normal text, 3:1 large text.

## Verification

Run `scripts/check_policy_accessibility.py <local-path-to-axe.min.js>` with axe-core 4.10.3. It tests 15 representative pages in light/dark/high-contrast themes, narrow layout, keyboard task menus/sorting/disclosures/skip link, runtime external requests, and cookie names. Results are written to ignored `.test-policy-audit/results.json`. Automated findings do not certify full accessibility or legal compliance.

The completed browser audit found zero WCAG A/AA rule violations on those 45 page/theme combinations, zero JavaScript errors, and no third-party runtime requests. The separate workspace check passed 35 responsive checks plus settings/theme saving and AI draft creation. These are bounded test results, not a full assistive-technology certification.
