# Databank integration — stub

A working stub of the two-way API between COMPASS CMP and Databank, built from
the brief *COMPASS CMP and Databank integration brief* (7 Oct 2026). Use it to
build and test CMP's side while the contract is still being agreed.

Everything in the brief is a proposal, and so is everything here. The stub
fixes nothing in place: field names, endpoints and timings follow the brief
and change when the two teams agree otherwise.

## What it is

| Piece | Where | What it does |
|---|---|---|
| Contracts | `backend/api/src/cmp/integration/databank/contracts.py` | Every message in the brief as a typed model: the lab delivery, and the requests and responses of the six calls |
| CMP's endpoints (calls 1, 2, 6) | `backend/api/src/cmp/api/routers/integration/databank.py` | Asset events with verdicts, consent lookup, instruction results |
| Verdict rules | `…/databank/verdicts.py` | `valid`, `restricted`, `invalid`, `unknown`, per person and per asset, from a mock consent register (`fixtures.json`) |
| Reliability rules | `…/databank/store.py`, `…/databank/service.py` | Idempotent IDs, rising `asset_version`, asset IDs never reused — in memory |
| CMP's client (calls 3, 4, 5) | `…/databank/client.py` | Inventory, consent changes, instructions; timeout, bounded retries with jitter |
| Mock Databank | `…/databank/mock_server.py` | Databank's half: hosts calls 3–5, quarantines a lab delivery and registers it with CMP, carries out instructions and reports back |
| Draft OpenAPI | `docs/integration/databank/openapi.json` | The six calls in one document, generated from the models |
| Demo | `…/databank/demo.py` | Walks the whole flow once against running servers |

## The six calls

| # | Call | Endpoint | Hosted by |
|---|---|---|---|
| 1 | Asset events | `POST /integration/v1/asset-events` | CMP |
| 2 | Consent lookup | `GET /integration/v1/consents/{consent_id}` | CMP |
| 3 | Inventory | `GET /integration/v1/persons/{person_id}/assets` | Databank (mock) |
| 4 | Consent changed | `POST /integration/v1/consent-events` | Databank (mock) |
| 5 | Instructions | `POST /integration/v1/instructions` | Databank (mock) |
| 6 | Instruction results | `POST /integration/v1/instructions/{instruction_id}/results` | CMP |

## Run it

```bash
cd backend/api
export DATABANK_SERVICE_TOKEN=$(python -c "import secrets; print(secrets.token_hex(24))")

# 1. The API with the stub on
DATABANK_STUB_ENABLED=true .venv/bin/python -m cmp --port 8000

# 2. The mock Databank (another terminal, same token)
.venv/bin/python -m cmp.integration.databank.mock_server --port 8100 \
    --cmp-url http://127.0.0.1:8000            # add --redaction to support redaction

# 3. Walk the flow once (another terminal, same token)
.venv/bin/python -m cmp.integration.databank.demo \
    --cmp-url http://127.0.0.1:8000 --databank-url http://127.0.0.1:8100
```

The mock's own controls are at `http://127.0.0.1:8100/docs` (`/mock/deliveries`,
`/mock/assets`, release and delete). CMP's stub memory is at
`GET /integration/v1/stub/state` (with the token; not one of the six calls).

Tests: `.venv/bin/python -m pytest tests/unit/integration` — contracts, the
verdict rules, the reliability rules, and both sides together in process.

Regenerate the OpenAPI draft after changing a contract:

```bash
.venv/bin/python -m cmp.integration.databank.openapi > ../../docs/integration/databank/openapi.json
```

## The mock consent register

`fixtures.json` holds four consents, all on the brief's example project and site:

| Person | Consent | State | An asset captured 5 Oct is |
|---|---|---|---|
| `1f6b9d3a…` | `c41e7a90…` (the brief's) | in force, two purposes | valid |
| `7a2d4c81…` | `e95b1f04…` (the brief's) | partly withdrawn, research only | valid for research |
| `3c8e5a17…` | `0b6f2d18…` → `4d9c1e52…` | withdrawn 6 Oct | restricted (invalid if captured after) |
| `5f3b8d26…` | `8e1a7c35…` | expired 30 Sep | invalid |

Any other consent ID is `unknown`; a person, project or site that does not
match the consent is `invalid`. Point `DATABANK_STUB_FIXTURES` at your own
file to try other cases.

## Safety

- **Off by default.** `DATABANK_STUB_ENABLED` mounts the endpoints; the settings
  refuse it in production and refuse a token shorter than 32 characters.
- **A service identity on every call.** A bearer token compared in constant
  time — a stand-in for mutual TLS or signed tokens.
- **Internal network only.** The console's and the portal's `/api` proxies no
  longer forward `/api/integration` (`next.config.ts` in each app).
- **Identifiers only.** No model has a field for a name, a contact or asset
  content; the logs carry IDs, types, statuses and verdicts.
- **Nothing written to the database.** The store is in memory; no migration.

## Choices the brief left open

These are the stub's guesses, for the joint session to confirm or change:

1. **`deleted` and `released` events** name the asset with `asset_id` (no full
   record). `deleted` carries `reason`; `released` carries
   `release: {recipient, released_on}`.
2. **Event results** have a `status` of `accepted`, `duplicate`,
   `ignored_stale` or `rejected`, with a `detail`. A repeated `event_id` returns
   the first answer exactly.
3. **Strictness** when an asset holds several people: `invalid` > `unknown` >
   `restricted` > `valid`.
4. **Consent events** travel in a batch, `{"events": [{event_id, consent}]}`, and
   are acknowledged with `{accepted, duplicates}`.
5. **Instructions** are answered `202 Accepted` with `{instruction_id, status,
   duplicate}`.
6. **Instruction results** are acknowledged with how the instruction now
   stands: `{items_reported, items_done, complete}`.
7. **Unknown fields are ignored**, because within a version a change only adds
   fields.
8. **The mock's redaction** fails with `redaction_not_supported` unless started
   with `--redaction`. A legal hold makes an erasure fail with `legal_hold`.

## What replaces the stub

| Stub | The real thing |
|---|---|
| `MockConsentResolver` (fixture file) | A resolver over the consent register and its supersession chain, behind the same `ConsentResolver` protocol |
| `IntegrationStore` (memory) | Tables for events, asset versions, deleted IDs and instruction results, with the same three rules |
| Bearer token | Mutual TLS or signed tokens |
| Calls 4 and 5 sent directly | An outbox: a durable queue with retries, so an outage delays a message and never loses one |
| `/integration/v1/stub/state` | Removed |
