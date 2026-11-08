# Auth: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

15 operations; 15 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| POST | `/auth/login` | public | No session required; anonymous COND |
| POST | `/auth/logout` | `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder` | Full session; anonymous NO |
| GET | `/auth/me` | `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder` | Full session; anonymous NO |
| POST | `/auth/mfa/resend` | `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder` | Valid session (partial or full) + CSRF; anonymous NO |
| POST | `/auth/mfa/verify` | `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder` | Valid session (partial or full) + CSRF; anonymous NO |
| POST | `/auth/otp/request` | public | No session required; anonymous YES |
| POST | `/auth/otp/verify` | public | No session required; anonymous COND |
| POST | `/auth/password/change` | `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder` | Full session; anonymous NO |
| POST | `/auth/password/reset/confirm` | public | No session required; anonymous COND |
| POST | `/auth/password/reset/request` | public | No session required; anonymous YES |
| POST | `/auth/register` | public | No session required; anonymous YES |
| POST | `/auth/register/verify` | public | No session required; anonymous COND |
| GET | `/auth/sessions` | `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder` | Full session; anonymous NO |
| DELETE | `/auth/sessions/{session_uuid}` | `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder` | Full session; anonymous NO |
| GET | `/auth/sso/callback` | public | No session required; anonymous COND |

## POST /auth/login

Staff sign-in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No existing session. Only active staff accounts can complete password sign-in; data_subject accounts are refused. MFA is required for staff by default, subject to deployment configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L155), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/logout

End this session.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |

- **Who:** `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `CurrentUser`.
- **Rules:** Ends the caller’s current session only.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L295), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## GET /auth/me

Who is signed in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |

- **Who:** `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `CurrentUser`.
- **Rules:** Returns the caller’s effective session role and navigation; account_role may differ after OTP portal sign-in.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L312), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/mfa/resend

Resend the MFA code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND | COND | NO | NO |

- **Who:** `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `PartialUser`.
- **Rules:** A valid session cookie and CSRF token are required. Despite its name, PartialUser does not enforce session.partial or restrict roles; the handler loads the current account and requests its MFA code.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L198), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/mfa/verify

Complete stepped-up sign-in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND | COND | NO | NO |

- **Who:** `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `PartialUser`.
- **Rules:** A valid session cookie and CSRF token plus the account MFA code are required. PartialUser accepts partial or full sessions; it has no role filter. Successful promotion requires an issued code. It stamps the account's email proved, where the code went; the code never goes to the mobile (2026-11-08).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L181), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/otp/request

Data-subject sign-in code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Public entry point. Codes go to registered contacts; an eligible staff account can also use the portal as a data principal. Each code is issued under the account and the keyed hash of the contact it goes to, so it answers only to that contact (2026-11-08).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L242), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/otp/verify

Data-subject sign-in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Rules:** A valid contact code opens a session acting as data_subject, even when the underlying account is staff. The code verifies only with the contact it was sent to: another contact of the same account, a code of the wrong length and a spent budget of five tries answer 400 otp_invalid "Invalid or expired code", as a wrong code and an unknown contact do, so no refusal says whom the register knows; only the limit of 30 failures in fifteen minutes per address answers 429. It stamps that contact proved - the mobile, the email or the second email typed - and no other (2026-11-08).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L279), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/password/change

Password Change.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |

- **Who:** `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `CurrentUser`.
- **Rules:** Own account only; the current password must verify. No staff-only role guard exists; passwordless accounts cannot satisfy the password check.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L326), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/password/reset/confirm

Password Reset Confirm.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Public entry point; an account-specific reset/invitation code is required. This activates a pending invited account. It stamps the account's email proved: a reset, a staff invitation and a breach holder's invitation all send this code there. A wrong code, a code of the wrong length and a spent budget of five tries answer 400 otp_invalid "Invalid or expired code", as an email with no account does; only the limit of 30 failures in fifteen minutes per address answers 429 (2026-11-08).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L345), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/password/reset/request

Password Reset Request.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Public entry point; a reset code is issued only for eligible active/pending staff accounts. The response does not reveal account existence.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L338), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/register

Data-subject self-registration.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Public self-registration creates a data_subject account; callers cannot choose a staff role. Contact verification is required. A date of birth under eighteen creates no account (S2-01). It is refused before the contact is looked up, 422 minor_not_permitted on dob, the same for a contact nobody holds, a data principal's sign-up never finished and any account, with nothing sent or written; only the limit of five an hour per contact comes first. Until 7bdb710 it was checked after the lookup, and a child's date answered 202 for an unfinished sign-up, 422 for a contact nobody holds and 409 for an account. A data principal's sign-up never finished answers 202 as a new contact does, and its codes are sent again, to the contacts it was first given. A contact on any other account answers 409 contact_taken, naming the field, by product decision, and nothing is sent to it: since 7bdb710 that includes a member of staff's or a breach holder's account still pending its first password, which until then was answered 202 and sent sign-up codes no sign-up could use.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L215), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## POST /auth/register/verify

Finish sign-up: every medium given answers with its code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Public entry point; valid registration contact codes are required to complete registration. Every refusal answers 400 otp_invalid "Invalid or expired code" on mobile_code, as an unknown mobile does: a mobile nobody holds or one on an account that cannot finish a sign-up (a member of staff's, or a suspended or deactivated one), an account with nothing left to answer, a code left out for a contact still waiting, and a wrong code, one of the wrong length or a spent budget for either contact. Every code waiting is checked before any is spent. Failures count against the address, and only the limit of 30 failures in fifteen minutes per address answers 429, even to the right codes once it is spent. Until bd6cef1 a code left out answered 422 and a refusal came on the field of the contact waiting (email_code when only the email was), with no limit per address, which told an unfinished sign-up and an account whose email had not answered from a mobile nobody holds. Refusing an account with nothing left to answer closed a hole (32d483a): from 2026-09-06 until 2026-11-08 the mobile alone, with no code, opened a session on a data principal's account whose every contact had answered once.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L260), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## GET /auth/sessions

Your active sessions.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |

- **Who:** `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `CurrentUser`.
- **Rules:** Lists sessions belonging to the signed-in account only.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L354), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).

## DELETE /auth/sessions/{session_uuid}

Revoke one of your sessions.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN | OWN | NO | NO |

- **Who:** `admin`, `data_subject`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `CurrentUser`.
- **Rules:** The target session must belong to the caller; another account’s session is not selectable.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/auth.py#L364), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/auth/authentication/service.py#L52), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authentication.py#L61).
## GET /auth/sso/callback

Where the organisation's identity provider returns (ADR 0034).

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | NO | NO |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** The state the start issued is the credential, taken once: unknown or used is a 404. Exchanges the code, validates the ID token, matches the employee ID, and redirects (303) to the link with `?sso=` ok, mobile, conflict, invalid, unavailable or cancelled; sets a data principal's session on a match, or the pending cookie for a new employee. Never records a claim. (2026-10-28, ADR 0034) A sign-in to an account already there stamps no contact proved; only creating one does. Whether the assertion should stamp the address there too is open (breaches.md, 2026-11-08).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/public/consent.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/auth.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/auth/authentication/sso.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/infrastructure/identity/oidc.py), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/infrastructure/identity/state.py).
