# Authorisation

Two questions, deliberately answered by different things.

## 1. May this role call this at all?

A static matrix: 22 resources × 7 roles → a grant. The whole table is laid out in
[docs/domain/roles-and-access.md](../domain/roles-and-access.md). Checked before any work is
done, by `RequireResource` or `RequireRole`.

Two conventions:

* **A resource absent from the matrix is denied to everyone.** New endpoints fail
  closed; somebody has to add a row deliberately.
* **A role absent from a resource's row is denied it.** No wildcard, no
  inheritance. A role that should see something is named.

## 2. Which rows may this user see?

A `Scope`, which a repository turns into a WHERE predicate.

| Scope | Means |
|---|---|
| `ALL` | every row |
| `SCOPED` | rows assigned to them — for a collection owner, the projects and sites they own, plus a colleague's for a period of cover; for the administrator on `rights_request`, escalated grievances only |
| `OWN` | rows they created, or that are about them — for `ticket`, every staff role, since a respondent answers only the tickets addressed to them |
| `NONE` | no rows |

**Never a filter applied after the fetch.** A row already in the response has
already been counted and has already moved a cursor. The repositories compile the
scope into SQL, so a row outside scope is never selected — which means the
service cannot forget to filter, because there is nothing to filter.

## 403 versus 404

**403 means visible but not permitted.** Anything outside your scope is 404. A
403 confirms the row exists, and existence is the fact the scope was meant to
withhold — a caller walking uuids must not be able to tell "not yours" from "not
there".

**A hidden resource answers 404 to a role with no grant at all.** Ordinarily a
role the matrix denies a resource is told 403 - the route exists and is not for
them. For `breach` that answer would itself say something: a 403 on
`/breaches/{uuid}` confirms the uuid is a breach. So its guards are
`RequireResource("breach", hidden=True)`, which raises `NotFound` instead, and
every other role reads the register, a real breach and a made-up uuid exactly
alike. `tests/security/test_breach_is_hidden.py` and the HTTP suite hold it.

## Where it lives

| Module | Holds |
|---|---|
| `core/permissions.py` | `Role`, `Scope`, `Grant`, `MATRIX`, `NAV_BY_ROLE` — data, no behaviour |
| `auth/authorization/roles.py` | staff/privileged sets, the MFA rule |
| `auth/authorization/resources.py` | the 22 resource names as constants; the roster and the matrix are asserted equal at import |
| `auth/authorization/scopes.py` | `ScopeContext`, `narrower_of` |
| `auth/authorization/evaluator.py` | pure decisions, returning a reason |
| `auth/authorization/policy.py` | `authorize()` — the front door; logs the denial |
| `api/dependencies/authorization.py` | the FastAPI guards |

The table is in `core` because four repositories read a scope out of it, and
`db` must not import from a layer above it. `core` holds the vocabulary and the
table; `auth` holds everything you do with it.

## Denials are recorded

Every 403, and every 404 that stands in for one on a hidden resource
(`HiddenFromRole`, raised by `RequireResource(..., hidden=True)`), writes an
`auth.access_denied` audit row. The API's error handler writes it, on a
connection of its own, once the request's transaction has rolled back - a row
written in that transaction would roll back with it. `detail.resource` is the
method and route template (`GET /audit`, never a uuid from the path),
`detail.cause` the error's code (`forbidden`, `csrf_failed`) or `hidden`, and
`detail.role` the caller's role. A caller told "not found" is still recorded as
refused: the trail knows what the response does not say. An access-control
system that refuses correctly
but silently is half a system: the refusal is what tells an operator that
somebody is probing, or that a role was provisioned wrongly, or that a permission
change broke a legitimate workflow.

The message never says *why*. "Your role does not permit this" tells a legitimate
user to ask their administrator; a specific reason tells somebody probing which
door is closest to open.

## The audit trail is writable by nobody

Two roles can read it. No role can write it — and that is enforced four deep:
the route is not registered, the matrix has no write grant, the `UPDATE` and
`DELETE` privileges are revoked from the application's database role (migration
0003), and a trigger refuses the statement (0002).

The Privacy Office is audited by this table. A DPO who can edit her own audit
trail makes it worthless as evidence.

## What a portal opens rests on this

Personal values leave the API sealed, and the portals open them in their own
server route ([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)).
That route makes no authorisation decision of its own: the decision is the one
this page describes, made when the API chose which rows to serve. How far the
route itself relies on that, and whether it should check more, is under
review; see [csrf.md](csrf.md#not-covered-the-portals-own-dkmsdecrypt).
