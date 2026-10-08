# 0009. Two portals, split by audience, one API

Status: accepted. September 2026. Supersedes the single frontend. Amended
2026-10-08: the portal also serves a rights ticket's outside holder - see the
end and [ADR 0024](0024-a-rights-tickets-holder-is-reached-three-ways.md).

## Context

One Next.js application served both the staff console and everything a data
principal used: the consent flow, sign-up, the rights pages, her own
records. The two audiences have opposite needs. Staff pages carry the
registers and want a shell, navigation and dense tables; a data principal
arrives from a link on a phone, once, and must not see a hint of the
console. Shipping both in one bundle meant every staff route existed on the
public hostname and every public change re-tested the console.

## Decision

Two deployments from one API:

| Portal | Audience | Port |
|---|---|---|
| `frontend/console` | staff: password and code sign-in, the registers, the rights queue, tickets | 3000 |
| `frontend/portal` | data principals and the public: `/c/{token}`, sign-up, code sign-in, rights, her records | 3001 |

Nothing a member of staff uses ships on the portal and nothing a data
principal uses ships on the console. Each portal proxies `/api` from its own
origin, and each points the wrong kind of account at the other. The API
carries two base URLs, `PUBLIC_BASE_URL` and `CONSOLE_BASE_URL`, so a link in
an email lands on the right one.

They share a design system, a layered `src/lib`, the error contract as a
type, and the rule that neither holds a copy of the permission matrix or the
state machine.

## Consequences

- Two builds, two test suites, two dev servers; the shared code is
  duplicated by copy, not by a package, which is a known cost.
- A public-surface change cannot break the console's bundle.
- The data principal's origin exposes no staff route to enumerate.

## Revisit when

The shared `src/lib` drifts between the two. A workspace package would be
the fix.

## Amended 2026-10-08: outside ticket holders

The portal now also serves people who are neither staff nor data principals:
a vendor or third-party processor that holds a person's data and answers a
rights ticket. It opens `/ticket/{token}`, enters a one-time code sent to the
address on the ticket, and answers there (migration 0049,
[ADR 0024](0024-a-rights-tickets-holder-is-reached-three-ways.md)). The page
reaches one ticket and nothing of the console, so the split above stands:
nothing a member of staff uses ships on the portal. A holder inside the
organisation still answers on the console.
