# 0011. The serving of a notice is the server's record, not the client's claim

Status: accepted. September 2026. Supersedes the echoed `served_at`.

## Context

Section 5(1) requires the notice to be given before or with the request for
consent. The artefact records `served_at`, and the design said it was
server-stamped: `GET /c/{token}/notice` set it and the page echoed it back
with the consent. Echoing is the weakness. The capture route accepted any
recent timestamp in the body, and a caller who never rendered the notice
could record a consent that looked like every other. The September 2026
review did exactly that.

## Decision

When the notice is rendered to a signed-in person, the server writes its own
record of the serving in Redis: keyed on the person, the link and the
rendition; holding the moment and the text hash; lasting six hours. Recording
a consent requires that record, takes `served_at` from it, and refuses with
`notice_not_served` when there is none. The body field is accepted and
ignored for older clients, and the portal no longer sends it. Capture also
re-checks that the rendition is approved, so the guarantee does not depend on
the caller having gone through the render.

Redis rather than a table because the record is ephemeral by nature and the
artefact is where the durable fact lands. Six hours because that was already
the staleness window.

## Consequences

- A consent cannot exist without a serving the server witnessed, to that
  person, through that link, in that language.
- A page open longer than six hours must reload the notice; the code says so.
- Every test that records a consent through the service renders the notice
  first, and the integration suite opens Redis for every test.
- A Redis outage stops consent capture. Redis was already required for the
  session that capture needs.

## Revisit when

An audit requirement asks for the serving to be durable on its own. It would
then become a row, and the artefact would reference it.
