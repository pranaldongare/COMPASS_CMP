# 0004. Scope is compiled into the query; out of scope is 404, not 403

Status: accepted.

## Context

Seven roles see different rows of the same tables. A filter applied after
the fetch has already counted the row, moved the cursor, and loaded it into
memory; and a service that must remember to filter will one day forget.

## Decision

The permission matrix in `core/permissions.py` gives each (resource, role)
a scope: `ALL`, `SCOPED`, `OWN` or `NONE`. Repositories compile the scope
into the SQL `WHERE` clause, so a row outside scope is never selected. The
service cannot forget to filter because there is nothing left to filter.

A row outside scope answers 404. 403 is reserved for a row the caller can
see but may not act on, and every 403 is audited. A caller walking uuids
cannot tell "not yours" from "not there", which is the fact the scope was
meant to withhold.

The matrix is data, not code: no wildcard, no inheritance, a resource absent
from it is denied to everyone. The console draws its navigation from the
server's computed sections and holds no copy.

## Consequences

- A new resource is a new row in the matrix and a scope predicate in its
  repository. Both are asserted at import and by a test, so forgetting one
  fails the process, not a user.
- Site scope is stricter than project scope on purpose: a collection owner
  who reaches a project through one site cannot act on a colleague's site.
- Cover (delegation) widens a delegate's scope for a period by adding the
  delegator's rows to the predicate, never by changing their role.
- The security suite walks uuids across roles and expects 404.

## Revisit when

A role needs row-level rules the four scopes cannot express. So far every
case has fitted.
