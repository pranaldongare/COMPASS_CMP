"""The OIDC client's validation, against a stub provider's real signatures (ADR 0034).

An assertion signs a person in on the provider's word, so every way that word
can be forged or misdirected is refused: another issuer, another audience,
another sign-in's nonce, an expired token, a signature by a key the provider
never published, an algorithm we do not accept, and an assertion without the
employee ID the account is matched on. A provider that does not answer is a
different failure from all of those, and is reported as one.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from tests.support.oidc_stub import CLIENT_ID, ISSUER, StubProvider, install

from cmp.infrastructure.identity import oidc

NONCE = "nonce-for-this-sign-in"


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> Iterator[StubProvider]:
    with install(monkeypatch) as provider:
        yield provider


async def test_a_good_token_yields_the_claims(stub: StubProvider) -> None:
    claims = await oidc.validate(stub.id_token(nonce=NONCE), nonce=NONCE)
    assert claims.employee_id == "EMP-1001"
    assert claims.email == "asha.rao@corp.example"
    assert claims.name == "Asha Rao"


@pytest.mark.parametrize(
    "fault",
    [
        {"issuer": "https://elsewhere.example"},
        {"audience": "another-client"},
        {"expires_in": -3600},
        {"key": "unpublished"},
        {"nonce": "another-sign-in"},
    ],
    ids=["issuer", "audience", "expired", "signature", "nonce"],
)
async def test_each_fault_is_refused(stub: StubProvider, fault: dict[str, Any]) -> None:
    kwargs: dict[str, Any] = {"nonce": NONCE}
    if fault.get("key") == "unpublished":
        kwargs["key"] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    else:
        kwargs.update(fault)
    with pytest.raises(oidc.AssertionInvalid):
        await oidc.validate(stub.id_token(**kwargs), nonce=NONCE)


async def test_an_unsigned_token_is_refused(stub: StubProvider) -> None:
    token = jwt.encode(
        {"iss": ISSUER, "aud": CLIENT_ID, "sub": "x", "nonce": NONCE, "employee_id": "E1"},
        key=None,
        algorithm="none",
    )
    with pytest.raises(oidc.AssertionInvalid):
        await oidc.validate(token, nonce=NONCE)


async def test_an_hmac_token_is_refused(stub: StubProvider) -> None:
    """A client secret is not a provider's signature."""
    token = jwt.encode(
        {"iss": ISSUER, "aud": CLIENT_ID, "sub": "x", "nonce": NONCE, "employee_id": "E1"},
        key="s3cret-s3cret-s3cret-s3cret-s3cret",
        algorithm="HS256",
    )
    with pytest.raises(oidc.AssertionInvalid):
        await oidc.validate(token, nonce=NONCE)


async def test_an_assertion_without_the_employee_id_is_refused(stub: StubProvider) -> None:
    with pytest.raises(oidc.AssertionInvalid):
        await oidc.validate(stub.id_token(nonce=NONCE, employee_id=None), nonce=NONCE)


async def test_a_rotated_key_is_followed(stub: StubProvider) -> None:
    await oidc.validate(stub.id_token(nonce=NONCE), nonce=NONCE)  # caches key-1
    stub.rotate()
    claims = await oidc.validate(stub.id_token(nonce=NONCE), nonce=NONCE)
    assert claims.employee_id == "EMP-1001"


async def test_the_code_is_exchanged_with_its_verifier(stub: StubProvider) -> None:
    token = stub.id_token(nonce=NONCE)
    code = stub.code_for(token)
    assert await oidc.exchange(code=code, verifier="v" * 43) == token
    with pytest.raises(oidc.AssertionInvalid):
        await oidc.exchange(code=code, verifier="v" * 43)  # a code works once


async def test_the_authorisation_url_carries_pkce_and_the_nonce(stub: StubProvider) -> None:
    verifier, challenge = oidc.pkce_pair()
    url = await oidc.authorize_url(state="st", nonce=NONCE, challenge=challenge)
    assert url.startswith(f"{ISSUER}/authorize?")
    assert "code_challenge_method=S256" in url
    assert f"code_challenge={challenge}" in url
    assert f"nonce={NONCE}" in url
    assert verifier not in url


async def test_a_provider_that_does_not_answer_is_not_an_invalid_assertion(
    stub: StubProvider,
) -> None:
    stub.down = True
    with pytest.raises(oidc.ProviderUnavailable):
        await oidc.discovery()
    assert await oidc.reachable() is False
    stub.down = False
    assert await oidc.reachable() is True
