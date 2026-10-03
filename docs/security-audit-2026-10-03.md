# Security review — October 3, 2026

## Implemented and verified in application code

| Request | Status |
| --- | --- |
| HSTS | Already enabled for secure production sessions, one-year max-age. Render redirects HTTP to HTTPS. No unverified subdomain/preload commitment. |
| CSRF tokens | Now enforced centrally for every registered unsafe-method route. Server-rendered POST forms supply tokens; session extension sends `X-CSRF-Token`. Same-origin write checks remain additional protection. |
| Password-change sessions | Existing `auth_version` invalidates other sessions. The current session now also rotates its CSRF token. Password changes are limited to five attempts per 15 minutes per account, plus connection limits. |
| Expiring/rate-limited password resets | No active password-reset flow or reset emails. Retired reset URLs return 404. Do not invent a recovery service or an untested reset-token guarantee. Any future recovery implementation needs single-use, hashed, expiring tokens and generic rate-limited responses. |
| User enumeration | Sign-in returns the same message for an unknown username and wrong password; unknown accounts still run a dummy password hash check. Login/signup/transfer attempts are throttled. Username signup availability remains observable when a new account succeeds; this is not a claim of complete enumeration resistance. |
| Upload types | Calendar uploads require an `.ics` name and an allowed calendar/plain-text/binary MIME type, then actual iCalendar parsing, size/event limits, and user review. Client MIME alone is not trusted. Files are not persisted or served as executable uploads. Browser backup restoration stays local and validates its data structure. |
| Prompt injection | AI receives only selected text and minute budget, has no tools/database credentials/remote document retrieval, returns bounded validated JSON, and requires explicit human review. Generated links/markup are rejected. This contains impact; it cannot guarantee that every misleading instruction or suggestion is detected. |
| AI usage | Existing atomic five/user/day, one/minute, and 100/site/day limits retained. Provider responses and request duration are bounded. |
| Request size | Existing 2 MiB total request cap; 1 MiB calendar limit; 16 KiB auth/AI request checks. No unlimited upload route. |
| Input handling | Validate types, ranges, lengths, allowed values, and URLs; reject unsupported control characters in task/course text. Preserve legitimate plain text, escape it when rendering, use DOM text APIs and SQLAlchemy-bound parameters. Do not HTML-encode everything before storage or strip meaningful mathematical punctuation. |
| CORS | No cross-origin access-control allow headers or permissive CORS extension. Browser API connections restricted to self by CSP; external navigation still works. |
| Directory listing/admin | No directory index or default admin route. Tests verify `/static/` and `/admin` return 404. |
| Security logs | Structured login success/failure, CSRF/cross-site rejection, rate-limit, upload-type rejection, and password-change events. Only event/outcome/route endpoint and optional internal user ID; never passwords, tokens, raw IPs, AI prompts, or submitted task text. Render log access/retention still needs operator management. |
| Cookies/secrets | HttpOnly, SameSite=Lax, Secure on Render/production. Render now refuses the development secret fallback if `SECRET_KEY` is missing. Never publish environment values. |
| Database privileges | Runtime least privilege requires owner-side PostgreSQL/Render configuration. `AUTO_MIGRATE=0` now lets a pre-migrated database run without startup DDL; default `1` preserves existing deployments. See the procedure below. |

## Database owner procedure (not executed against production)

The current startup performs schema creation/migrations, so simply revoking DDL would break deployment. Use a separate schema owner/migration credential and a non-owner runtime credential.

1. Back up the database and apply pending migrations using the existing owner credential in a controlled maintenance environment. Keep that credential out of the web service's runtime environment afterward.
2. In an owner/admin `psql` session, create a dedicated role if your managed database account permits it:

```sql
CREATE ROLE studentsuccess_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
\password studentsuccess_runtime
SELECT format('GRANT CONNECT ON DATABASE %I TO studentsuccess_runtime', current_database()) \gexec
GRANT USAGE ON SCHEMA public TO studentsuccess_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO studentsuccess_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO studentsuccess_runtime;
```

3. Verify effective privileges, including inherited `PUBLIC` grants. The runtime role must not own schemas/tables or have schema CREATE, database CREATE, role creation, superuser, or schema-owner membership. A REVOKE on the individual role cannot cancel a privilege inherited from PUBLIC. Review any PUBLIC changes with the database owner before applying them because they can affect other applications.
4. Point the **web service's** `DATABASE_URL` at the internal connection using that runtime role, and set `AUTO_MIGRATE=0` in the same service environment. Keep the secret only in Render, not source code. Redeploy and verify login, task writes, exports, and deletion.
5. Future migrations must run with the separate owner credential before application deployment. Grant the runtime role access to any newly created tables/sequences. Define owner-specific default privileges only after checking which role actually creates future objects.
6. Review the database's external-access/IP restrictions in Render. Retain only connections you actually need; internal application traffic should use the internal URL in the same region.

Read-only privilege inspection, when connected as the runtime role:

```sql
SELECT current_user, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user;
SELECT has_schema_privilege(current_user, 'public', 'CREATE') AS can_create_schema_objects;
SELECT has_database_privilege(current_user, current_database(), 'CREATE') AS can_create_schemas;
```

No production role or database access setting was changed by this review. Confirm role creation support and a rollback connection before switching credentials.

## Verification and limits

`tests/test_security_hardening.py` uses the raw Flask client to reject missing tokens on every registered POST route, exercise valid form/header tokens, session invalidation, upload allowlists, escaped script-like text, AI link/markup rejection, privacy-safe logs, headers, and retired routes. Older business-logic tests use `BrowserFormClient` to submit the token that actual rendered forms now supply; the production guard is never disabled, even in testing mode. Existing negative CSRF tests retain raw submissions.

Verification: the full suite passed 413 tests and exposed one legacy unauthenticated-form test missing its new CSRF token. After updating that test, all 44 task/security tests passed. Native browser sign-in and 35 responsive workspace checks, including task creation, AI draft approval, and settings, passed. Automated checks are not a penetration test or a guarantee of complete security. Current CSP still permits inline scripts/styles because the application uses them; a nonce-based CSP is a separate migration, not silently claimed here.

References: [Flask security guidance](https://flask.palletsprojects.com/en/stable/web-security/), [OWASP prompt-injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [Render PostgreSQL connections](https://render.com/docs/postgresql-creating-connecting).
