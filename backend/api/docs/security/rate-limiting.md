# Rate limiting

Every unauthenticated surface is bounded, and each bound is keyed on the
thing an attacker cannot cheaply rotate.

| Surface | Bound | Keyed on | Why |
|---|---|---|---|
| Sign-in | 5 attempts / 30 min, 30 min lockout | **account** | An attacker rotates addresses; a NAT'd office should not be locked out by one typo |
| OTP verify | 5 attempts per code | code | The cap is what makes six digits strong enough |
| OTP request | 5 / hour per contact, 20 / hour per link | contact | Otherwise the form is an SMS pump aimed at someone else's number |
| Public link | 60 / minute | address | Unauthenticated, and there is no account to key on |

Every bucket is a Redis key `rate:<bucket>:<identity>`, which is what a test
suite clears between runs. The buckets in use:

| Bucket | Guards |
|---|---|
| `subject_register`, `subject_otp` | self-registration and the data principal's sign-in code, per contact |
| `consent_otp_contact`, `consent_otp_token` | codes sent from the consent flow, per contact and per link |
| `mfa_resend`, `pwreset` | a staff member asking for another second-factor code; password reset |
| `public_link` | `/c/{token}`, per address |
| `rights_public_contact`, `rights_public_ip`, `rights_verify_ip` | the public rights form and its verification; a request is neutral, so the address is the only handle a stranger has |
| `nominee_start`, `nominee_start_ip`, `nominee_request_ip` | a nominee identifying themselves and acting |
| `nomination_view_ip`, `nomination_act_ip` | opening and answering an acceptance link, so a link-holder cannot guess a code |

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
