# Enable verified email accounts

Email signup is prepared but stays off until mail delivery is configured. Existing
private codes and older username accounts continue to work. No user data is moved
or deleted when the feature is enabled.

## Setup on Render

1. Create a Resend account and verify a sending domain you control:
   https://resend.com/docs/dashboard/domains/introduction
2. Create a sending API key for that domain. Keep it in Render's environment settings,
   never in source control, chat, screenshots, or a browser-side variable.
3. Set these environment variables on the existing web service:

   ```text
   RESEND_API_KEY=<your sending key>
   EMAIL_FROM=StudentSuccess <accounts@your-verified-domain.example>
   PUBLIC_BASE_URL=https://studentsuccess.onrender.com
   ```

   Use the actual verified sender instead of the example address. If you later use a
   custom site domain, update `PUBLIC_BASE_URL` to its HTTPS origin (no trailing path).
   The fixed origin prevents request Host headers from changing recovery links.
4. Redeploy. Signup and sign-in switch to the email flow automatically, and Settings
   offers existing users **Upgrade to email sign-in**. New private-code creation stops;
   existing codes still work until their owners choose to upgrade.
5. With an email account you control, check signup, inbox delivery, confirmation, sign-in,
   password reset, and Settings. Test an existing planner upgrade and confirm its tasks
   and courses remain. Verify that spam filtering and the sender identity are correct.

Delivery uses Resend's HTTPS API without an additional SDK:
https://resend.com/docs/api-reference/emails/send-email

## Account behavior

- Email is stored only as a verified account identifier after confirmation. Names,
  student IDs, and contact details are still excluded from task/course notes.
- Verification and recovery links last 30 minutes, work once, and require an explicit
  form submission. Opening a link in an email scanner does not consume it.
- Only a token digest and password hash are stored. Pending requests are removed after
  expiry on subsequent authentication requests. Request limits persist in the database;
  throttle identifiers use keyed hashes rather than raw addresses or IPs.
- Upgrades require the current private code/password and email confirmation. They update
  the same user ID, retain its data, disable the old code, and invalidate old sessions.
- Password recovery invalidates prior sessions and returns to sign-in. Changing a
  password from Settings also invalidates other sessions.
- Outbound email errors leave current access intact. They never expose provider responses
  or tokens in the page or application logs. Do not enable request-body logging for these
  routes; treat confirmation URLs and provider email logs as account secrets.
- Existing verified email accounts can still sign in if delivery is temporarily disabled;
  use the **Sign in with email** link. Do not remove delivery settings as a long-term
  rollback: recovery requires working email. Old code accounts remain usable.

## Verified locally; external setup still required

Automated tests use a fake transport and exercise token replay/expiry, CSRF, delivery
failure, request limits, migration preservation, login and session revocation. Browser
tests cover the enabled email UI and signup confirmation. Real domain verification,
delivery, sender reputation and inbox placement must be checked after setup.
