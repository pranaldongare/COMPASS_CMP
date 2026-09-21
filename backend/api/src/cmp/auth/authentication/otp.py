"""One-time codes, for data-subject sign-in, staff MFA and the public consent flow.

Properties that matter, and why:

* **The code is never stored.** Redis holds a keyed digest. A dump of the store
  does not let anyone complete a sign-in that is in flight.
* **The scope is part of the digest.** A code issued for a consent link cannot be
  replayed against `/auth/otp/verify`, because a different scope hashes to a
  different value even for the same six digits.
* **Attempts are counted against the code, not the connection.** Five wrong
  guesses discard the code (API reference §1.6). Counting per connection means
  an attacker with two connections gets ten.
* **Verification is single-use and atomic.** The check, the delete and the
  attempt count are one server-side script, so two racing requests cannot both
  succeed with the same code. (Before September 2026 the check was a `GET`
  and the delete a later pipeline, and a review reproduced two concurrent
  callers both being told yes.)

Six digits is a million-space, which is only safe *because* of the attempt cap
and the ten-minute lifetime. Neither control is optional.
"""

from __future__ import annotations

from dataclasses import dataclass

from cmp.core.config import settings
from cmp.core.errors import BadRequest, RateLimited
from cmp.core.logging import get_logger
from cmp.core.security import hash_otp, new_otp
from cmp.db.redis import K_OTP, K_OTP_ATTEMPTS, get_redis, key

log = get_logger("cmp.otp")


class Scope:
    """A code is only valid for the flow it was issued for."""

    SUBJECT_LOGIN = "subject_login"
    CONSENT_LINK = "consent_link"
    STAFF_MFA = "staff_mfa"
    CONTACT_VERIFY = "contact_verify"
    #: A rights request from the public form, verified against the stored
    #: channel. Keyed on the request reference.
    RIGHTS_VERIFY = "rights_verify"
    #: A nominee acting under s.14, verified against the contact she recorded.
    NOMINEE_VERIFY = "nominee_verify"
    #: Sign-up authenticating every medium given. Keyed on the account and the
    #: medium: "<uuid>:mobile", "<uuid>:email".
    SUBJECT_REGISTER = "subject_register"
    #: A nominee proving a recorded contact before the link's accept or decline
    #: counts. Keyed on the nomination uuid.
    NOMINATION_ACCEPT = "nomination_accept"


@dataclass(frozen=True, slots=True)
class Issued:
    code: str  # delivered out of band; never returned by an API response
    expires_in_s: int


def _ckey(scope: str, identity: str) -> str:
    return key(K_OTP, scope, identity)


def _akey(scope: str, identity: str) -> str:
    return key(K_OTP_ATTEMPTS, scope, identity)


async def issue(scope: str, identity: str, *, ttl_s: int | None = None) -> Issued:
    """Generate and store a code for (scope, identity).

    Issuing replaces any outstanding code and resets the attempt counter, so a
    user who asks for a new code is not locked out by their own typos on the old
    one. Rate limiting on *requesting* a code lives at the route, where the
    per-contact and per-token quotas differ.
    """
    ttl = ttl_s or settings.otp_ttl_s
    code = new_otp()
    r = get_redis()
    pipe = r.pipeline()
    pipe.setex(_ckey(scope, identity), ttl, hash_otp(code, scope=scope))
    pipe.delete(_akey(scope, identity))
    await pipe.execute()

    # The code itself is never logged. The fact of issuance is.
    log.info("otp.issued", scope=scope, ttl_s=ttl)
    return Issued(code=code, expires_in_s=ttl)


#: Compare, consume and count in one step on the server. A `GET` followed by a
#: `DEL` is two round trips, and two requests carrying the same correct code
#: could both read the digest before either deleted it - both would succeed,
#: and "single use" would be a comment rather than a property. Redis runs a
#: script atomically, so the check and the consequence cannot be interleaved.
#:
#: The digest comparison inside the script is a plain string equality rather
#: than a constant-time one. The value compared is an HMAC over the secret key,
#: never the code itself, and the attempt budget caps a guess at five tries;
#: neither a timing side channel over a network round trip nor five samples
#: gets an attacker anywhere near a 256-bit digest.
#:
#: Returns {outcome, attempts}: 1 = matched, 0 = wrong (attempts so far),
#: 2 = wrong and the budget is spent (code discarded), -1 = no code stored.
_VERIFY_SCRIPT = """
local stored = redis.call('GET', KEYS[1])
if not stored then
  return {-1, 0}
end
if stored == ARGV[1] then
  if ARGV[2] == '1' then
    redis.call('DEL', KEYS[1], KEYS[2])
  end
  return {1, 0}
end
local attempts = redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], tonumber(ARGV[4]))
if attempts >= tonumber(ARGV[3]) then
  redis.call('DEL', KEYS[1], KEYS[2])
  return {2, attempts}
end
return {0, attempts}
"""


async def verify(scope: str, identity: str, code: str, *, consume: bool = True) -> bool:
    """Check a code once. Consumes it on success; discards it after N failures.

    `consume=False` checks without spending: a flow that has to see two codes
    pass before it acts uses it for the first, so a wrong second code does not
    burn a first that was right. Failures count against the code either way.

    The check, the consumption and the attempt count happen in one atomic
    server-side step (see `_VERIFY_SCRIPT`), so of two racing requests with
    the same correct code exactly one is told yes.
    """
    r = get_redis()
    ck, ak = _ckey(scope, identity), _akey(scope, identity)

    script = r.register_script(_VERIFY_SCRIPT)
    outcome, attempts = await script(
        keys=[ck, ak],
        args=[
            hash_otp(code, scope=scope),
            "1" if consume else "0",
            str(settings.otp_max_verify_attempts),
            str(settings.otp_ttl_s),
        ],
    )
    outcome, attempts = int(outcome), int(attempts)

    if outcome == -1:
        log.info("otp.verify_no_code", scope=scope)
        return False

    if outcome == 1:
        log.info("otp.verified", scope=scope, consumed=consume)
        return True

    if outcome == 2:
        # Discarded entirely rather than merely refused. A code that survives
        # its attempt budget is a code being brute-forced.
        log.warning("otp.discarded_after_attempts", scope=scope, attempts=attempts)
        raise RateLimited(
            "Too many incorrect attempts. Request a new code.",
            retry_after_s=0,
        )

    log.info("otp.verify_failed", scope=scope, attempts=attempts)
    return False


async def require(
    scope: str, identity: str, code: str, *, field: str = "code", consume: bool = True
) -> None:
    """Verify or raise. The message is identical for a wrong code and an expired
    one - distinguishing them tells an attacker which half of the problem to fix."""
    if not code.isdigit() or len(code) != settings.otp_length:
        raise BadRequest("Invalid code", code="otp_invalid", field=field)
    if not await verify(scope, identity, code, consume=consume):
        raise BadRequest("Invalid or expired code", code="otp_invalid", field=field)


async def discard(scope: str, identity: str) -> None:
    r = get_redis()
    await r.delete(_ckey(scope, identity), _akey(scope, identity))
