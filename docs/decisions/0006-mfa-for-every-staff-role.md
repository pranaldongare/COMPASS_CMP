# 0006. An emailed second factor for every staff role

Status: accepted. September 2026. Supersedes the earlier rule that only the
DPO and the administrator had a second factor.

## Context

Every staff role can reach personal data: a collection owner sees the people
at their sites, an R&D user sees consents on their project, a respondent sees
what a rights request asks for. The original rule protected the two roles
that could change the platform and left the roles that could read the data
with a password alone.

## Decision

Every role except the data principal signs in with a password and then a
six-digit code sent to the account's email, valid for five minutes and five
attempts. The list is `MFA_REQUIRED_ROLES`, and its **default is derived from
the role enumeration** minus the data principal, so a role added later is
covered on arrival rather than by remembering to add it.

A deployment may narrow the list in configuration and answers for that. The
data principal has no password; her sign-in already is a code, to the mobile
or email she chooses.

## Consequences

- Staff accounts must have an email; the database requires it with a CHECK.
- Local development reads codes from the outbox; the browser suite reads the
  same file.
- A staff sign-in is two steps everywhere, including the test fixtures.
- The partial session between the steps authorises the verification route
  only.

## Revisit when

A hardware or app-based factor is required by policy. The step is the same;
the transport changes.
