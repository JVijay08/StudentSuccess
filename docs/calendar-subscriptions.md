# Calendar subscriptions

Calendar now offers a read-only subscription for active task titles and deadlines. A new calendar_subscriptions table is created by the existing startup schema initialization. Only a SHA-256 hash of the random 256-bit bearer token is stored. The link is shown once, can be replaced or revoked, and is invalidated by password changes and disabling calendar export. Account deletion removes it. Tutorial accounts cannot create subscriptions. Feed responses are private/no-store and excluded from indexing.

Treat subscription URLs as secrets, including in proxy/access logs. Anyone holding a link can read its calendar. Do not publish it or include it in support screenshots. Calendar providers retain copies; revoking a link prevents future retrieval but does not erase provider caches. Delete the subscribed calendar there. Refresh timing depends on the calendar client, not StudentSuccess. This is one-way subscription, not Google OAuth synchronization. Existing one-time exports remain available.

## Google OAuth remains configuration-dependent

No Connect Google button is shown because there is no configured OAuth client. Completing that integration needs a Google Cloud project with Calendar API enabled, consent-screen configuration, web OAuth client credentials, approved HTTPS redirect URI, server-side encrypted refresh-token storage, and synchronization/retry handling. Request only the calendar permissions needed for a dedicated app-created calendar; do not request unrelated Google account data. Keep secrets server-side.

Official references: https://developers.google.com/identity/protocols/oauth2/web-server and https://developers.google.com/workspace/calendar/api/auth

## Other review limits

Course preparation checks compare catalog prerequisite names to recorded courses. They are advisory, not enrollment validation. Graduation certification is not added: verified jurisdiction/cohort requirements and credit mappings are missing. Weekly workload checks preserve student-entered hours and compare combined college courses in the same term with their study budget; they do not silently replace high values.
