"""COMPASS CMP <-> Databank: a stub of the two-way integration (2026-10-12).

From the brief "COMPASS CMP and Databank integration brief" (Oct 7, 2026).
Every field name, endpoint and timing in it is a proposal still to be agreed
with the Databank team, so this package is a stub to build and test against,
not the integration itself:

* `contracts` - the six calls and the lab delivery metadata, as typed models.
  The same models drive the CMP endpoints, the client and the mock Databank, so
  the OpenAPI they produce is the draft specification the brief asks for.
* `verdicts` - how CMP judges an asset's subjects. `MockConsentResolver` reads
  a fixture file; the real resolver will read the consent register.
* `store` - idempotency and version ordering, in memory. The real store will be
  durable.
* `client` - CMP's side of calls 3, 4 and 5 (Databank hosts them): an HTTP
  client, and an in-process mock.
* `mock_server` - a runnable mock Databank: it hosts calls 3, 4 and 5, takes a
  lab delivery and registers it with CMP (call 1), and reports instruction
  results back (call 6).

CMP's own endpoints (calls 1, 2 and 6) are `cmp.api.routers.integration`,
mounted only when `DATABANK_STUB_ENABLED` is set (never in production).

What crosses: identifiers and metadata only. No names, contacts or asset
content - none of the models has a field that could carry them, and nothing
here logs more than identifiers.
"""
