"""The two endpoints, against the contract exactly as it was specified."""

from __future__ import annotations

from typing import Any

#: The caller's own example, unchanged. If this stops passing, the contract
#: moved, and moving it is not something to discover from a failing portal.
SPEC_EXAMPLE: dict[str, Any] = {
    "data": [
        {"employeeID": "E-0001", "fullName": "Amruta Shukla", "emailId": "amruta@example.org"},
        {"employeeID": "E-0002", "fullName": "Anuj Kumar", "emailId": "anuj@example.org"},
    ],
    "key": {"fullName": "NAME", "emailId": "EMAIL"},
    "method": "string",
}


def test_the_specified_request_is_accepted_as_written(client: Any) -> None:
    r = client.post("/bulk_encrypt", json=SPEC_EXAMPLE)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["records"] == 2
    assert body["values"] == 4
    for original, encrypted in zip(SPEC_EXAMPLE["data"], body["data"], strict=True):
        # Only what the key named.
        assert encrypted["employeeID"] == original["employeeID"]
        assert encrypted["fullName"].startswith("SE::")
        assert encrypted["emailId"].startswith("SE::")
        assert original["fullName"] not in encrypted["fullName"]


def test_a_batch_comes_back_out_the_way_it_went_in(client: Any) -> None:
    """Order is the contract every caller relies on without saying so."""
    data = [{"i": str(n), "fullName": f"Person {n}"} for n in range(500)]
    key = {"fullName": "NAME"}

    sealed = client.post("/bulk_encrypt", json={"data": data, "key": key}).json()["data"]
    opened = client.post("/bulk_decrypt", json={"data": sealed, "key": key}).json()["data"]

    assert [r["i"] for r in opened] == [r["i"] for r in data]
    assert [r["fullName"] for r in opened] == [r["fullName"] for r in data]


def test_the_bytes_method_round_trips(client: Any) -> None:
    body = {**SPEC_EXAMPLE, "method": "bytes"}
    sealed = client.post("/bulk_encrypt", json=body).json()

    assert not sealed["data"][0]["fullName"].startswith("SE::")

    opened = client.post(
        "/bulk_decrypt", json={"data": sealed["data"], "key": body["key"], "method": "bytes"}
    ).json()
    assert opened["data"][0]["fullName"] == "Amruta Shukla"


def test_fields_outside_the_key_are_never_touched(client: Any) -> None:
    data = [
        {"fullName": "Amruta Shukla", "employeeID": "E-1", "salary": 100, "tags": ["a"], "x": None}
    ]
    out = client.post("/bulk_encrypt", json={"data": data, "key": {"fullName": "NAME"}}).json()

    record = out["data"][0]
    assert record["employeeID"] == "E-1"
    assert record["salary"] == 100
    assert record["tags"] == ["a"]
    assert record["x"] is None


def test_a_null_stays_null_and_a_missing_field_stays_missing(client: Any) -> None:
    """Encrypting an absence would invent a value that means something."""
    data = [{"fullName": None}, {"employeeID": "E-2"}]
    out = client.post(
        "/bulk_encrypt", json={"data": data, "key": {"fullName": "NAME", "emailId": "EMAIL"}}
    ).json()

    assert out["data"][0]["fullName"] is None
    assert "fullName" not in out["data"][1]
    assert out["values"] == 0


def test_running_the_same_batch_twice_does_not_encrypt_it_twice(client: Any) -> None:
    """The failure this prevents is silent and unrecoverable by one decrypt."""
    once = client.post("/bulk_encrypt", json=SPEC_EXAMPLE).json()["data"]
    twice = client.post("/bulk_encrypt", json={"data": once, "key": SPEC_EXAMPLE["key"]}).json()

    assert twice["data"] == once
    assert twice["values"] == 0
    assert twice["skipped"] == 4

    opened = client.post(
        "/bulk_decrypt", json={"data": twice["data"], "key": SPEC_EXAMPLE["key"]}
    ).json()
    assert opened["data"][0]["fullName"] == "Amruta Shukla"


def test_the_wrong_type_in_the_key_refuses_the_batch(client: Any) -> None:
    sealed = client.post("/bulk_encrypt", json=SPEC_EXAMPLE).json()["data"]

    r = client.post(
        "/bulk_decrypt",
        json={"data": sealed, "key": {"fullName": "EMAIL", "emailId": "EMAIL"}},
    )

    assert r.status_code == 422
    errors = r.json()["detail"]["errors"]
    assert errors[0]["field"] == "fullName"
    assert errors[0]["index"] == 0
    assert "NAME" in errors[0]["message"]


def test_skip_keeps_the_good_records_and_reports_the_bad(client: Any) -> None:
    """What a migration over rows of unknown vintage actually needs."""
    sealed = client.post("/bulk_encrypt", json=SPEC_EXAMPLE).json()["data"]
    sealed.append({"employeeID": "E-0003", "fullName": "SE::not-real", "emailId": None})

    out = client.post(
        "/bulk_decrypt",
        json={"data": sealed, "key": SPEC_EXAMPLE["key"], "on_error": "skip"},
    ).json()

    assert out["data"][0]["fullName"] == "Amruta Shukla"
    assert out["data"][2]["fullName"] == "SE::not-real"  # left as it arrived
    assert [e["index"] for e in out["errors"]] == [2]


def test_an_unknown_data_type_is_refused_before_any_work_happens(client: Any) -> None:
    r = client.post(
        "/bulk_encrypt",
        json={"data": [{"fullName": "x"}], "key": {"fullName": "SHOE_SIZE"}},
    )
    assert r.status_code == 422


def test_an_empty_batch_is_refused(client: Any) -> None:
    assert client.post("/bulk_encrypt", json={"data": [], "key": {"a": "NAME"}}).status_code == 422
    assert client.post("/bulk_encrypt", json={"data": [{}], "key": {}}).status_code == 422


def test_a_batch_past_the_limit_is_refused_rather_than_attempted(client: Any) -> None:
    client.app.state.max_records = 3
    try:
        r = client.post(
            "/bulk_encrypt",
            json={"data": [{"fullName": "x"}] * 4, "key": {"fullName": "NAME"}},
        )
        assert r.status_code == 413
        assert "limit is 3" in r.json()["detail"]
    finally:
        client.app.state.max_records = 5000


def test_the_roster_of_types_is_published(client: Any) -> None:
    """So a caller writing a key mapping does not have to read the source."""
    types = client.get("/types").json()["types"]
    assert {"NAME", "EMAIL", "MOBILE", "DOB", "FREE_TEXT"} <= set(types)


def test_health_says_what_it_is_running(client: Any) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["provider"] == "local-aes-gcm"
    assert body["workers"] == 4


def test_the_first_paths_still_answer(client: Any) -> None:
    """`/encrypt/bulk` and `/decrypt/bulk` were the names for a week. A caller
    written against them is not broken by the rename."""
    sealed = client.post("/encrypt/bulk", json=SPEC_EXAMPLE)
    assert sealed.status_code == 200
    opened = client.post(
        "/decrypt/bulk", json={"data": sealed.json()["data"], "key": SPEC_EXAMPLE["key"]}
    )
    assert opened.json()["data"][0]["fullName"] == "Amruta Shukla"


# ------------------------------------------------------------- auto_decrypt
#
# The shape the deployed key service answers on: `{"payload": {k: sealed}}`
# in, `{"data": {k: plain}}` out, types read off each envelope. The platform
# uses it for values whose envelope it cannot read itself.


def test_auto_decrypt_opens_values_of_different_types_without_being_told(client: Any) -> None:
    sealed = client.post(
        "/bulk_encrypt",
        json={
            "data": [{"n": "Amruta Shukla", "e": "amruta@example.org", "m": "+919876543210"}],
            "key": {"n": "NAME", "e": "EMAIL", "m": "MOBILE"},
            "method": "string",
        },
    ).json()["data"][0]

    r = client.post(
        "/auto_decrypt", json={"payload": {"v0": sealed["n"], "v1": sealed["e"], "v2": sealed["m"]}}
    )

    assert r.status_code == 200
    assert r.json() == {
        "data": {"v0": "Amruta Shukla", "v1": "amruta@example.org", "v2": "+919876543210"}
    }


def test_auto_decrypt_refuses_what_it_cannot_open_naming_the_key_not_the_value(client: Any) -> None:
    r = client.post(
        "/auto_decrypt", json={"payload": {"good": "SE::bm90LWFuLWVudmVsb3Bl", "plain": "hello"}}
    )

    assert r.status_code == 422
    assert sorted(r.json()["detail"]["keys"]) == ["good", "plain"]
    assert "hello" not in r.text


def test_auto_decrypt_refuses_an_empty_payload(client: Any) -> None:
    assert client.post("/auto_decrypt", json={"payload": {}}).status_code == 422
