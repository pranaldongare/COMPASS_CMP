"""A stub OpenID Connect provider, in-process (ADR 0034, open point OP-1).

Serves a discovery document, a key set and a token endpoint through an
`httpx.MockTransport`, and signs ID tokens with an RSA key of its own, so the
client's validation runs against a real signature. A test hands the client
this transport (`install`), registers what a code should exchange for
(`code_for`), and can make the provider fail (`down = True`), rotate its key,
or sign with a key it never published.
"""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from cmp.core.config import settings
from cmp.infrastructure.identity import oidc

ISSUER = "https://idp.example.test"
CLIENT_ID = "cmp-portal"


def _key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StubProvider:
    def __init__(self) -> None:
        self.key = _key()
        self.kid = "key-1"
        self.codes: dict[str, str] = {}
        self.down = False
        self.token_calls = 0

    # --------------------------------------------------------------- tokens
    def rotate(self) -> None:
        self.key = _key()
        self.kid = f"key-{secrets.token_hex(2)}"

    def id_token(
        self,
        *,
        nonce: str,
        employee_id: str | None = "EMP-1001",
        email: str | None = "asha.rao@corp.example",
        name: str | None = "Asha Rao",
        issuer: str = ISSUER,
        audience: str = CLIENT_ID,
        expires_in: int = 300,
        key: rsa.RSAPrivateKey | None = None,
        kid: str | None = None,
        **extra: Any,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": issuer,
            "aud": audience,
            "sub": f"sub-{employee_id or 'none'}",
            "iat": now,
            "exp": now + expires_in,
            "nonce": nonce,
            **extra,
        }
        if employee_id is not None:
            claims["employee_id"] = employee_id
        if email is not None:
            claims["email"] = email
        if name is not None:
            claims["name"] = name
        return jwt.encode(
            claims, key or self.key, algorithm="RS256", headers={"kid": kid or self.kid}
        )

    def code_for(self, token: str) -> str:
        code = secrets.token_urlsafe(16)
        self.codes[code] = token
        return code

    # -------------------------------------------------------------- serving
    def _jwks(self) -> dict[str, Any]:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        jwk.update({"kid": self.kid, "use": "sig", "alg": "RS256"})
        return {"keys": [jwk]}

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectTimeout("the provider did not answer", request=request)
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "jwks_uri": f"{ISSUER}/jwks",
                },
            )
        if path == "/jwks":
            return httpx.Response(200, json=self._jwks())
        if path == "/token":
            self.token_calls += 1
            form = dict(httpx.QueryParams(request.content.decode()))
            token = self.codes.pop(form.get("code", ""), None)
            if token is None or not form.get("code_verifier"):
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"id_token": token, "token_type": "Bearer"})
        return httpx.Response(404)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)


@contextmanager
def install(monkeypatch: Any) -> Iterator[StubProvider]:
    """The client pointed at a fresh stub provider, with SSO switched on."""
    stub = StubProvider()
    monkeypatch.setattr(settings, "sso_enabled", True)
    monkeypatch.setattr(settings, "sso_issuer", ISSUER)
    monkeypatch.setattr(settings, "sso_client_id", CLIENT_ID)
    monkeypatch.setattr(
        settings, "sso_client_secret", settings.sso_client_secret.__class__("s3cret")
    )
    monkeypatch.setattr(oidc, "_transport", stub.transport)
    oidc.forget()
    try:
        yield stub
    finally:
        oidc.forget()
