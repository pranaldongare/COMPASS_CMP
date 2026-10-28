"""OpenID Connect, Authorization Code with PKCE, against one provider (ADR 0034).

Four things, and nothing about who the person is to the platform: the
provider's discovery document, the URL a browser is sent to, the exchange of
the code the provider returns for an ID token, and the validation of that
token - signature against the provider's published keys, issuer, audience,
expiry and the nonce this sign-in was started with. What an assertion means
(which account, whether a new one) is `cmp.auth.authentication.sso`'s.

Two failures, kept apart because a person is told different things: the
provider did not answer (`ProviderUnavailable`: try again), and the
assertion is not one to trust (`AssertionInvalid`: the same neutral page as
an invalid link). Neither ever carries the claims.

The provider is reached over httpx with `settings.sso_timeout_s`. Discovery
and the key set are cached for an hour; a token signed with a key the cache
has not seen is checked once against a fresh key set, which is how a
provider's key rotation is followed. `_transport` lets the tests put a stub
provider in front of the client.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from cmp.core.config import settings
from cmp.core.logging import get_logger

log = get_logger("cmp.sso")

#: How long discovery and the key set are trusted before they are fetched again.
CACHE_S = 3600
#: The algorithms an ID token may be signed with. Never `none`, never HMAC
#: (a client secret is not a provider's signature).
ALGORITHMS = ("RS256", "RS384", "RS512", "ES256", "ES384", "PS256")
#: Leeway for the provider's clock and ours.
LEEWAY_S = 60

#: Set by the tests: an httpx transport that answers as a provider would.
_transport: httpx.AsyncBaseTransport | None = None
_cache: dict[str, tuple[float, Any]] = {}


class ProviderUnavailable(Exception):
    """The provider did not answer, or answered with an error of its own."""


class AssertionInvalid(Exception):
    """The provider's answer is not one to sign anybody in on."""


@dataclass(frozen=True, slots=True)
class Claims:
    """What the platform takes from an assertion, and nothing else."""

    subject: str
    employee_id: str
    email: str | None
    name: str | None


def configured() -> bool:
    return bool(settings.sso_enabled and settings.sso_issuer and settings.sso_client_id)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.sso_timeout_s, transport=_transport)


async def _get_json(url: str) -> dict[str, Any]:
    try:
        async with _client() as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise ProviderUnavailable(type(exc).__name__) from exc
    if response.status_code != 200:
        raise ProviderUnavailable(f"HTTP {response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise ProviderUnavailable("not JSON") from exc
    if not isinstance(body, dict):
        raise ProviderUnavailable("not an object")
    return body


async def _cached(name: str, fetch: Any, *, fresh: bool = False) -> Any:
    hit = _cache.get(name)
    if hit and not fresh and time.monotonic() - hit[0] < CACHE_S:
        return hit[1]
    value = await fetch()
    _cache[name] = (time.monotonic(), value)
    return value


def forget() -> None:
    """Drop what is cached; for the tests, and after a settings change."""
    _cache.clear()


async def discovery() -> dict[str, Any]:
    async def fetch() -> dict[str, Any]:
        doc = await _get_json(settings.sso_issuer.rstrip("/") + "/.well-known/openid-configuration")
        for field in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"):
            if not doc.get(field):
                raise ProviderUnavailable(f"discovery has no {field}")
        return doc

    doc: dict[str, Any] = await _cached("discovery", fetch)
    return doc


async def _keys(*, fresh: bool = False) -> dict[str, Any]:
    doc = await discovery()

    async def fetch() -> dict[str, Any]:
        return await _get_json(str(doc["jwks_uri"]))

    keys: dict[str, Any] = await _cached("jwks", fetch, fresh=fresh)
    return keys


def pkce_pair() -> tuple[str, str]:
    """A verifier the server keeps, and the challenge the browser carries."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def authorize_url(*, state: str, nonce: str, challenge: str) -> str:
    doc = await discovery()
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.sso_client_id,
            "redirect_uri": settings.sso_redirect_url,
            "scope": settings.sso_scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    endpoint = str(doc["authorization_endpoint"])
    return f"{endpoint}{'&' if '?' in endpoint else '?'}{query}"


async def exchange(*, code: str, verifier: str) -> str:
    """The ID token for a code. Client secret by HTTP Basic, the verifier as
    PKCE asks."""
    doc = await discovery()
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.sso_redirect_url,
        "code_verifier": verifier,
        "client_id": settings.sso_client_id,
    }
    auth = (settings.sso_client_id, settings.sso_client_secret.get_secret_value())
    try:
        async with _client() as client:
            response = await client.post(str(doc["token_endpoint"]), data=form, auth=auth)
    except httpx.HTTPError as exc:
        raise ProviderUnavailable(type(exc).__name__) from exc
    if response.status_code >= 500:
        raise ProviderUnavailable(f"HTTP {response.status_code}")
    if response.status_code != 200:
        # A 4xx is the provider refusing this code: spent, expired, or not
        # ours. That is not an outage; it is an assertion we do not have.
        raise AssertionInvalid(f"token endpoint said {response.status_code}")
    try:
        token = response.json().get("id_token")
    except ValueError as exc:
        raise AssertionInvalid("token response not JSON") from exc
    if not isinstance(token, str) or not token:
        raise AssertionInvalid("no id_token")
    return token


async def _signing_key(token: str) -> Any:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AssertionInvalid("unreadable header") from exc
    if header.get("alg") not in ALGORITHMS:
        raise AssertionInvalid(f"algorithm {header.get('alg')!r} not accepted")
    kid = header.get("kid")
    for fresh in (False, True):
        for jwk in (await _keys(fresh=fresh)).get("keys", []):
            if kid is None or jwk.get("kid") == kid:
                try:
                    return jwt.PyJWK(jwk).key
                except jwt.PyJWTError:
                    continue
    raise AssertionInvalid("no published key signs this token")


async def validate(token: str, *, nonce: str) -> Claims:
    """The claims, once the signature, issuer, audience, expiry and nonce all
    hold; `AssertionInvalid` otherwise."""
    doc = await discovery()
    key = await _signing_key(token)
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=list(ALGORITHMS),
            audience=settings.sso_client_id,
            issuer=str(doc["issuer"]),
            leeway=LEEWAY_S,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AssertionInvalid(type(exc).__name__) from exc
    if not secrets.compare_digest(str(claims.get("nonce") or ""), nonce):
        raise AssertionInvalid("nonce does not match")
    employee_id = str(claims.get(settings.sso_claim_employee_id) or "").strip()
    if not employee_id:
        # An assertion without the number the HRMS knows cannot be matched to
        # anybody, and must not create an account nobody can be found by.
        raise AssertionInvalid("no employee id claim")
    email = claims.get(settings.sso_claim_email)
    name = claims.get(settings.sso_claim_name)
    return Claims(
        subject=str(claims["sub"]),
        employee_id=employee_id,
        email=str(email).strip().lower() if email else None,
        name=str(name).strip() if name else None,
    )


async def reachable() -> bool:
    """For `/ready`: whether the discovery document answers."""
    _cache.pop("discovery", None)
    try:
        await discovery()
    except ProviderUnavailable:
        return False
    return True
