# 0046: An employee is checked with VerifyEmail at sign-in

- Status: accepted
- Date: 2026-11-25
- Migration: 0075
- Related: [0035](0035-a-public-request-reaches-the-inside-only-when-the-inside-collects-it.md)
  (the relay), [0038](0038-datavault-is-asked-by-the-platform-at-an-address-the-administrator-sets.md)
  (DataVault, the pattern followed), [0044](0044-an-employee-link-takes-the-code-route-until-the-sign-in-is-connected.md)
  (employee links)

## Context

The organisation offered one call that says whether an address belongs to
somebody it employs now:

    POST {address}/VerifyEmail
    {"MySingleID": "someone@company.example"}

    200 {"MySingleID": "someone@company.example", "IsActive": true, "Status": true}

The product owner asked (2026-11-25) for it to be called whenever an existing
employee signs in - to the public portal, and to the console - with the
address and the organisation's email domains set by the administrator, as
DataVault's address is. Their answers to the questions this raised:

1. **Portal, not active:** sign in as an ordinary person. A former employee is
   still a data principal, with every right over their consents.
2. **No answer:** the portal goes ahead; the console refuses - except the
   administrator.
3. **Console:** staff on the organisation's domains are checked; staff on any
   other domain (testing uses cmp.local, test.com) are allowed for now, and
   that is to be switched off before production.
4. **Domains:** one list, the administrator's, which replaces
   `BREACH_TICKET_EMAIL_DOMAINS` (who is inside the organisation for breach and
   rights tickets).

## Decision

1. **The platform makes the call, from inside.** The API at a console
   sign-in; the worker after a portal sign-in. Nothing crosses the relay: a
   portal request reaches the API through the bridge, SQS and the collector as
   it always has, on routes already on the allow-list (ADR 0035), and the API
   asks VerifyEmail on its own side, as it asks DataVault. No route was added
   to the portal or to the allow-list.
2. **The address and the key are the administrator's** (resource
   `employee_check`, page *Employee check*). The key is encrypted with the
   application key and never served again. The address must be http or https
   with a host and nothing else; `/VerifyEmail` is added to it. Redirects are
   not followed. Switched off, nothing is asked anywhere and sign-in is as it
   was.
3. **What is sent is the email address, and nothing else. What is kept is the
   answer**: on the account (`employment_status`: active or inactive, NULL for
   never asked or no answer) and on the trail (`employee.checked`,
   `employee.check_failed`, with the flow and the result or a short failure
   code). The address asked about is never on the trail, and VerifyEmail's
   error body is never stored or logged.
4. **Active** is `Status` and `IsActive` both true. Anything else that reads
   cleanly is *inactive* (left, or not known). An answer about another
   address, or one whose flags are not JSON booleans, is no answer
   (`mismatch`, `unreadable`).
5. **Console sign-in** (`auth.authenticate`), after the password and before
   the code is sent - so a stranger never causes a call and a leaver is never
   sent a code: the administrator is never asked about; a member of staff on
   a company domain is asked, and *inactive* or no answer refuses, with a
   sentence saying why and `auth.login_failed` carrying the cause
   (`not_active_employee`, `employee_check_failed`); anyone on another domain
   signs in while `allow_other_domains` is on, and is refused
   (`not_organisation_domain`) once it is off. It starts on. It cannot be
   switched off with no domain listed, nor the last domain removed while it is
   off.
6. **Portal sign-in** (`auth.verify_subject_otp`), after the code: the worker
   (`cmp.employees.check_account`, queued after the commit) asks about the
   account's first address on a company domain - the email, then the second
   email; a person who signed in by mobile is asked about their email. Nobody
   is refused. A link made for employees (`audience_mode = sso`) refuses, when
   the notice is served and again when consent is captured, a person whose
   last answer was *inactive*; never asked, or no answer, goes ahead.
7. **One list of the organisation's domains** (`organisation_domain`),
   subdomains included. Migration 0075 seeds it from
   `BREACH_TICKET_EMAIL_DOMAINS`, once; from then on the administrator keeps
   it, and breach tickets (BD-12) and a rights holder's route read it.
   Changing the setting afterwards changes nothing.
8. **Health** counts the sign-ins VerifyEmail did not answer
   (`health.employee_check_failures`, by flow), and the *At a glance* board
   shows it.

## Consequences

- A VerifyEmail outage stops staff on the company domains signing in to the
  console until it answers. The administrator can always sign in, switch the
  check off, or allow other domains. This is the product owner's choice: the
  console fails closed, the portal fails open.
- Every console sign-in by staff on a company domain waits for one call (at
  most `EXTERNAL_HTTP_TIMEOUT_S`). The portal's does not.
- An employee-only link reads the last answer, which may be from the sign-in
  just made, or older, or none yet - the worker may not have answered by the
  time the link is followed. *None yet* goes ahead.
- An address somebody can set is a place the platform can be pointed at: one
  role, an address with nothing hidden in it, no redirect, every change on the
  trail (that the address or the key changed, never either).
- A development stand-in, `/dev/verify-email`, is mounted in local and test
  only: `left…` is a leaver, `unknown…` is not known, `down…` does not answer.

## Not decided here

- Whether a console account found inactive is switched off by the platform
  (today it is refused at sign-in; the administrator deactivates it).
- Asking again during a long session; today it is asked at sign-in only.
- Removing `allow_other_domains` altogether before production.
