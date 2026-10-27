# 0034. An employee consent link signs in through the organisation's SSO, and the account is matched on the employee ID

**Status:** proposed · 2026-10-27. Builds on
[ADR 0007](0007-mobile-first-contacts.md),
[ADR 0013](0013-every-account-is-a-data-principal.md) and
[ADR 0017](0017-lookup-by-keyed-hash-and-name-ngrams.md); amends ADR 0013.

## Context

A consent link authenticates a contact the register already knows and
enrols nobody (`docs/domain/consent-lifecycle.md`, "Who is signing"). That
is right for an external data principal and wrong for an employee: HR
activities reach thousands of employees who have never registered, whose
identity the organisation already asserts through its single sign-on, and
whose consent must be tied to an **employee ID** so that the HRMS can act on
it. `auth_user.organization_id` already exists for that number, sealed and
unique by keyed hash, but nothing matches a person on it today.

The product owner decided (2026-10-26) that an employee link signs in
through the organisation's SSO, that this applies to both tracks, that an
employee's mobile is mandatory with email optional so that the person can
still sign in by code after leaving, and that non-employee links keep the
one-time-code path.

## Decision

- **A consent link has an audience mode.** `consent_link.audience_mode` is
  `sso` or `otp`, chosen when the link is minted, on either track. An `otp`
  link behaves exactly as today. An `sso` link offers one way in: the
  organisation's identity provider.
- **OIDC Authorization Code with PKCE, one provider, behind an interface.**
  `infrastructure/identity/oidc.py` holds discovery, the authorisation
  redirect, the code exchange and ID-token validation (issuer, audience,
  nonce, signature, expiry). Settings: `SSO_ENABLED`, `SSO_ISSUER`,
  `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_REDIRECT_URL`, `SSO_SCOPES`,
  `SSO_CLAIM_EMPLOYEE_ID`, `SSO_CLAIM_EMAIL`, `SSO_CLAIM_NAME`. Production
  refuses `SSO_ENABLED=true` with an empty secret or a non-HTTPS issuer. If
  the organisation's provider turns out to speak SAML only, the interface
  gets a second implementation; the routes and the matching rule do not
  change.
- **The state is the server's.** `GET /c/{token}/sso/start` writes the
  state, the nonce, the PKCE verifier and the link token to Redis
  (`sso:*`, ten minutes) and redirects. `GET /auth/sso/callback` looks the
  state up once, exchanges the code, validates the ID token, and continues
  on the link it was started from. A callback with an unknown or used state
  is a 404 that says nothing else.
- **The account is matched on the employee ID, or created as an employee.**
  The claim named by `SSO_CLAIM_EMPLOYEE_ID` is hashed under
  `BLIND_INDEX_KEY` and compared with `organization_id_hash`. A match signs
  that account in. No match creates `auth_user` with `person_type =
  employee`, the asserted name and corporate email (sealed, hashed), the
  employee ID, `status = active`, `role = data_subject`, and
  `registered_via_link_id` set. An assertion whose email hash belongs to an
  account with a *different* employee ID is refused with a neutral message
  and audited (`auth.sso_identity_conflict`); the administrator resolves it.
- **The session is a data principal's.** Whatever the account's role, the
  callback mints the session through `open_principal_session` (ADR 0013):
  SSO on a consent link is worth exactly what a code is, no more.
- **Mobile stays mandatory for employees; the date of birth is asked once.**
  After the first SSO sign-in, before the notice is served, the person
  confirms a mobile by code (ADR 0007) and gives a date of birth if none is
  on record (`cmp.domain.users.age`). The two gates already exist for the
  code path; they move in front of the SSO path unchanged.
- **Leaving keeps the person.** Ending staff access or an HR status change
  does not touch the account's standing as a data principal; the person
  signs in later by code to the mobile or the personal email on the account
  (ADR 0013). The SSO path simply stops working when the directory no longer
  asserts them.
- **Employee ID is still never used to find a person in the open.**
  Registration, the public rights form and `/c/{token}/otp` do not accept an
  employee ID; only an assertion the provider signed carries one.

## Consequences

- An employee consents with no registration step; the artefact is bound to
  an account that carries the employee ID the HRMS knows, so the consented
  list an export produces can be acted on by employee number.
- `organization_id` becomes a matching key. Its uniqueness is already
  enforced on the hash; the new paths rely on it.
- The portal gains one page: "Continue with your organisation account" on an
  `sso` link, then the mobile and date-of-birth gates it already has.
- The platform now depends on an external identity provider for one path.
  `GET /ready` reports the provider's discovery document reachable when
  `SSO_ENABLED` is on, and an `sso` link whose provider is unreachable says
  the service did not answer and offers to try again, never that the link
  is invalid (review UX-3).
- ADR 0013 is amended: a sign-in by the organisation's SSO on a consent
  link mints a `data_subject` session, like a code; the assertion never
  carries a staff role.

## Revisit when

The organisation wants SSO for the staff console too (a different decision:
it replaces the password and the emailed second factor and changes
ADR 0006); or candidates and vendors appear in the directory and HR wants
them on the SSO path as well.
