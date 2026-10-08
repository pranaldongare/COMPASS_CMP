# Rate limiting

Every unauthenticated surface is bounded, and each bound is keyed on the
thing an attacker cannot cheaply rotate.

| Surface | Bound | Keyed on | Why |
|---|---|---|---|
| Sign-in | 5 attempts / 30 min, 30 min lockout | **account** - its uuid, whichever name was typed | An attacker rotates addresses; a NAT'd office should not be locked out by one typo |
| Sign-in, code sign-in, password reset | 30 **failures** / 15 min | address | The lockout protects one account from many guesses; this protects every account from one guesser. Only failures count, so an office signing in all morning never comes near it |
| OTP verify | 5 attempts per code, for as long as the code lives | code | The cap is what makes six digits strong enough |
| OTP request | 5 / hour per contact, 20 / hour per link | contact | Otherwise the form is an SMS pump aimed at someone else's number |
| Public link | 60 / minute | address | Unauthenticated, and there is no account to key on |
| An outside holder's ticket link | 60 / minute to open it, 20 / hour to ask for or enter a code; 5 codes / hour per ticket | address; ticket | The link is public; the code goes to the address on the ticket, so the per-ticket cap stops a mail pump at that address |

Every bucket is a Redis key `rate:<bucket>:<identity>`, which is what a test
suite clears between runs. The buckets in use:

| Bucket | Guards |
|---|---|
| `subject_register`, `subject_otp` | self-registration and the data principal's sign-in code, per contact |
| `contact_confirm` | a code to confirm a contact on one's own account, or one an administrator has just set; per contact, 5 an hour |
| `consent_otp_contact`, `consent_otp_token` | codes sent from the consent flow, per contact and per link |
| `mfa_resend`, `pwreset` | a staff member asking for another second-factor code; password reset |
| `public_link` | `/c/{token}`, per address |
| `rights_public_contact`, `rights_public_ip`, `rights_verify_ip` | the public rights form and its verification; a request is neutral, so the address is the only handle a stranger has |
| `nominee_start`, `nominee_start_ip`, `nominee_request_ip` | a nominee identifying themselves and acting |
| `nomination_view_ip`, `nomination_act_ip` | opening and answering an acceptance link, so a link-holder cannot guess a code |
| `nomination_code` | codes sent for one nomination's acceptance link, per nomination, 5 an hour |
| `holder_link_ip`, `holder_link_act_ip` | an outside holder's ticket link (0049): opening it, 60 a minute per address; asking for and entering a code, 20 an hour per address |
| `holder_ticket_code` | codes sent for one ticket's link, per ticket, 5 an hour |
| `login_fail_ip`, `otp_login_fail_ip`, `reset_fail_ip` | failed staff sign-ins, code sign-ins and password resets, per address (failures only) |

**The lockout counts the account, not what was typed.** `account_key()` keys
it on the account's uuid, so an email and a username are one budget; a login
that names no account is keyed on its keyed hash, so no typed login sits in
Redis in the clear. Until 5 October 2026 the counter was keyed on the typed
text: two names, two budgets. **A code's failure count lives as long as the
code** - until then it expired after `OTP_TTL_S` whatever the code's own life,
so a 48-hour staff invitation had five fresh guesses every ten quiet minutes.

**A contact bucket is keyed on the contact's keyed hash** (`contact_key()` in
`auth/rate_limit/service.py`): `index_of("contact", …)`, the normalised form the
account lookup uses. Every way of typing one phone - spaces, dashes, brackets,
`+91 98765 00001` and `+919876500001` - is one quota, as it is one person.
Until 1 October 2026 two buckets, `subject_otp` and `rights_public_contact`,
were keyed on the text as typed, so four spellings were four quotas - four
times the codes, and, since each new code resets its guess counter, four times
the guesses ([review SEC-2](../reviews/2026-10-01-frontend-architecture-review.md)).
The hash also means no contact sits in a rate key in the clear. An address
bucket holds the client IP, for as long as the window lasts, an hour at most.
The `otp:*` keys whose identity includes a contact (a contact confirmation's,
a consent link's) still hold it normalised but in the clear, among the few
places a contact sits in plaintext at rest
([encryption-at-rest.md](encryption-at-rest.md)).

**A new code resets the guess counter**, by design - a person who asks again
is not locked out by their own typos - so what bounds guessing is the issuing
quota: at most five codes an hour per contact, five tries each.

**Not everything is bounded.** The portals' own `POST /dkms/decrypt` has no
limit; see [csrf.md](csrf.md#not-covered-the-portals-own-dkmsdecrypt), where
it is recorded as under review.

## Why Redis and not memory

A counter in process memory is not a rate limit when there are four workers — it
is a limit four times looser than it claims, and nobody notices until the fifth
worker is added.

The same applies to lockout: an attacker who can reach any worker gets five
attempts *per worker*.

## Locks

`ratelimit.lock` provides a distributed lock for the operations that must not run
twice concurrently — publishing a notice, generating an export. Redis-backed for
the same reason.

## What a client sees

429 with `Retry-After`. The header is exposed through CORS, so a browser client
can actually read it and back off rather than hammering.
