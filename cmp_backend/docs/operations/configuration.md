# Configuration

One validated `Settings` object, 73 fields, in `core/config.py`. Every field is
documented in `.env.example`.

## Production refuses to start on

| Condition | Why |
|---|---|
| `SECRET_KEY` is the development default or under 32 bytes | Sessions and cursors are signed with it; a known key means forgeable sessions |
| `POSTGRES_PASSWORD` is `cmp`, `postgres` or empty | A default password is not a password |
| `COOKIE_SECURE` is false | The session travels in cleartext on the first `http://` hop |
| `DEBUG` is true | Turns a handled failure into a traceback carrying local variables |
| `CORS_ORIGINS` contains `*` | With `allow_credentials`, that hands the session to any origin |
| `EMAIL_TRANSPORT` is not `smtp` | The console transport writes nothing outside local/test; a code nobody receives is a sign-in nobody completes |
| `SMS_TRANSPORT` is not `http` | The same, for the data principal's primary sign-in; and `SMS_HTTP_URL` must be `https://` |

A service that boots with a known secret key is worse than one that does not
boot: the second failure is loud and costs ten minutes.

## Groups

| Group | Notable |
|---|---|
| Database | 15s statement timeout, 5s lock timeout — never infinite |
| Redis / Celery | Three logical databases, so a broker flush does not drop sessions |
| Session | 8h absolute, 30min idle; HttpOnly, Secure, SameSite=Lax |
| Lockout | 5 attempts / 30 min window / 30 min lockout |
| OTP & MFA | 6 digits, 10 minutes, 5 verify attempts; MFA codes live 5 minutes; `MFA_REQUIRED_ROLES` defaults to every staff role ([ADR 0006](../../../docs/decisions/0006-mfa-for-every-staff-role.md)) |
| URLs | `PUBLIC_BASE_URL` (the data-principal portal: consent and acceptance links) and `CONSOLE_BASE_URL` (the staff console: ticket and request links) |
| Rights | `RIGHTS_RESPONSE_PERIOD_DAYS` 90, `GRIEVANCE_RESPONSE_PERIOD_DAYS` 90, acknowledge 2, tickets 5, collate 5 before, download 30, unverified close 7, nomination accept 30 |
| Uploads | 25 MB; proofs are PDF, PNG, JPEG only |
| API | 50 default page size, 200 max; public link 60/min |
| Transports | `email_transport` (`console`, `smtp`, `null`), `sms_transport` (`console`, `http`, `null`), `storage_backend` (`local`; `object` is a stub that refuses on use). The `http` SMS transport POSTs `{"to","body","from"}` as JSON with a bearer token to `SMS_HTTP_URL`; put a provider-specific adapter in front of it |

## Transports default to not delivering

`console` for email and SMS, `local` for storage. A misconfigured staging box
that writes to a file is a far better failure than one that emails and texts real
people the first time somebody signs in.

Set `EMAIL_TRANSPORT=smtp` explicitly, along with the SMTP settings, to deliver
for real, and `SMS_TRANSPORT=http` with the gateway URL and token. Outside
local and test the console transports raise rather than pretend; in
production the settings refuse to load at all.

## Secrets

Belong in a secret manager. `.env` is gitignored from every directory in the
tree, and `.env.example` carries placeholders only.
