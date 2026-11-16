# 0040. Asking for a sign-in code says when there is no account

**Status:** accepted · 2026-11-16. No migration. Changes the reply decided with
the consent link's sign-in (2026-09-16) and kept by
[0013](0013-every-account-is-a-data-principal.md): "the same sentence whether or not the contact is
registered".

## Context

A person who typed a mobile or an email nobody had registered - on the portal's
sign-in or on a consent link - was told a code was on its way. None was, and
nothing said so: they waited, asked again, and left. The neutral reply was
there so the form could not be used to ask whether a number is on the
register. But sign-up has always answered that question: a contact already
taken is refused by name (`409 contact_taken`), and offered sign-in.

The product owner asked on 2026-11-16 for the plain answer: say there is no
account, and take the person to registration.

## Decision

1. `POST /auth/otp/request` and `POST /c/{token}/otp` answer a contact no
   account carries with `404 account_not_found`, field `contact`. Nothing is
   sent and nothing is recorded.
2. The portal takes the person to `/sign-up` with the contact filled in (a
   mobile as the mobile, an email as the email) and a notice at the top that
   there is no account for it. From a consent link, sign-up returns to the
   link afterwards (`next`).
3. The limits per contact, and per link, are counted before anybody is looked
   up, as before. So is the broker's outage, which answers everybody alike.
4. An account that is switched off is still answered as if a code went: why it
   is off is the administrator's to say, not a public form's.
5. The refusals of a code are unchanged: a wrong code, a spent one and one
   never sent are one sentence (`otp_invalid`).

## Consequences

- The form now says whether a contact has an account, to anybody who asks,
  five times an hour per contact. It says nothing else: not whose, not what
  they consented to. That is what sign-up already said.
- An `sso` link is unchanged: it sends no code and says the same sentence.
- The staff console's sign-in is unchanged: a wrong address and a wrong
  password are still one refusal.

## Also on 2026-11-16

- **The organisation sign-in's stand-in (`SSO_MOCK`) follows the browser.** Its
  page and its way back are paths, not addresses built from `PUBLIC_BASE_URL`,
  so it works where the portal is opened by IP from another machine or through
  the relay. And an address already on an account signs that account in, since
  the stand-in proved the address by a code as the ordinary sign-in does; with
  a real provider the same address is still a conflict (open point F-10).
  `SSO_MOCK` is still refused outside `local` and `test`.
