# 0044. An employee link takes the code route until the organisation's sign-in is connected

**Status:** accepted · 2026-11-17. No migration. Amends
[0034](0034-an-employee-link-signs-in-through-the-organisations-sso.md).

## Context

A consent link made for employees (`audience_mode = sso`) signed a person in
through the organisation's identity provider and no other way: no form and no
one-time code (ADR 0034). The Legal office's activity wizard offers that kind
of link first.

The organisation's sign-in is not connected yet. On any server where
`SSO_ENABLED` is off, every employee link therefore ended at "we could not
sign you in with your organisation account", and the development stand-in
(`SSO_MOCK`) is refused outside local and test. Employees could not give a
consent on an HR activity at all. The product owner asked on 2026-11-17 for
employees to take the normal route, as every other data principal does, until
the sign-in is integrated.

## Decision

1. **An employee link asks for the organisation account only while a sign-in
   is switched on**: `SSO_ENABLED`, or in development `SSO_MOCK`. Otherwise
   it is followed as a code link is: a new person registers by the form, and
   everyone signs in with a one-time code to their mobile or email.
2. **The link is not changed.** It stays `audience_mode = sso` in the
   register. The day the sign-in is connected, the same link asks for it; no
   link is made again and no data is migrated.
3. **One place decides**: `signs_in_with_the_organisation(link)` in
   `cmp.domain.consent.service`. The public link read tells the portal the
   mode in force, so the portal needs no change.
4. **The trail says so.** A registration through an employee link by form
   carries `employee_link_by_code` on its `subject.registered` row.

## Consequences

- Until the sign-in is connected, nothing vouches that a person on an
  employee link is an employee. Anyone holding the link can register and
  consent, as on any open link. An account made this way has no employee ID
  and takes the link's category as its person type, a hint and never a
  permission.
- When the sign-in is connected, a person who registered by code with the
  address the organisation asserts for them holds an account with that
  address and no employee ID. ADR 0034 treats that as a conflict (F-10) and
  does not sign them in. That rule has to be settled before the sign-in is
  switched on, for the accounts made meanwhile: see "Revisit when".
- Switching `SSO_ENABLED` on with a provider that is misconfigured still
  fails as before: the fallback is for "not connected", not for "connected
  and broken".
- The console says an employee link uses the organisation account "once it
  is connected, and a one-time code until then".

## Revisit when

- The organisation's sign-in is connected. Two things to decide then:
  whether an account that registered by code on an employee link is taken
  over by the organisation sign-in asserting the same address (today a
  conflict), and whether employee links made before then are closed and made
  again, so that every consent on them from then on is vouched for.
