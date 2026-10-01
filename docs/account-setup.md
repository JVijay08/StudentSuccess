# Account setup

Daily sign-in uses one nickname-style username and password. No email-sending service
or sender domain is needed. Passwords must contain 15 to 128 characters; username rules
are shown on the form. Save credentials in a password manager: lost passwords cannot
be reset through email or security questions.

After registration, the server requires `/onboarding` before any workspace route.
It stores education context, study budget, timezone, task defaults, and display choices.
Students can later edit these in Settings. Logging out, opening a direct URL, or using
another device cannot bypass the database completion flag. Tutorial practice workspaces are preconfigured.

Existing private-code users choose **Transfer it once** on the creation page, enter
the old code, and choose new credentials. Transfer preserves their user ID and all
planner data, removes the code, and revokes previous sessions. It then requires setup.
No new access codes are issued; `/access/*` and `/account/*` routes are removed.
Previously configured email accounts with an existing session can transfer using
their old password; email sign-in never launched on the hosted site.

Deployment automatically adds a non-null `onboarding_completed` column, default false.
Retired schema columns/tables are retained to avoid destructive migrations. Keep the
existing SECRET_KEY and persistent DATABASE_URL; do not enable demo reset for real data.
No RESEND_API_KEY, EMAIL_FROM, or PUBLIC_BASE_URL configuration is used.

Validation:
- `python -m pytest`
- `python scripts/check_account_setup.py`
- `python scripts/check_streamlined_workspace.py`
- `python scripts/audit_responsive.py`

The password policy follows the [OWASP authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
