# Layers

What each layer owns, what it may call, and what would be a bug.

## The rule

**A layer may only call the layer below it.** Everything else in this document
follows from that.

| Layer | May call | Must never |
|---|---|---|
| `bootstrap/` | everything | be imported by anything below it |
| `api/middleware` | the app | read a database row |
| `api/routers` | domain services, dependencies; `infrastructure/dkms` (see below) | write SQL, open a transaction it does not hand to a service |
| `api/dependencies` | `auth`, `core` | know the shape of any specific resource |
| `auth/` | `domain` repositories, `core`; `infrastructure/dkms` (see below) | import from `api` |
| `domain/` | repositories, `core`, `infrastructure` | import FastAPI, know an HTTP status code |
| `db/repositories` | `db/sql`, `core`; `infrastructure/dkms` (see below) | decide permission, call another repository |
| `tasks/` | `auth`, domain services, repositories, `infrastructure`, `core` | share a request's connection: a task is queued after the commit and runs in the worker |
| `infrastructure/` | `core`, `validation`, `db/redis`, each other | import from `domain`, `auth` or `api` |
| `core/` | nothing local | import from `db`, `domain`, `auth` or `api` |

## Why each boundary exists

### Routers are thin

A router validates the request shape, names its guard, calls one service, and
shapes the response. Business logic in a router is the single easiest way to end
up with two versions of a rule — one in the router and one in the service that a
task also calls.

### Services are the only writers

And the only callers of `audit.record()`. That is what makes "every change is
recorded" a property of the structure rather than a convention somebody has to
remember. A write that happened without an audit row is not a state the database
can reach, because both happen in the same transaction.

### Repositories do not decide permission

They receive a role and a scope and turn it into a WHERE predicate. A repository
that decided whether something was allowed would be a second authorisation
system, and the two would disagree.

### `core/` imports nothing local

Half the codebase needs to name a `Role`. If `core` imported from `auth`, then
`db`, `domain` and `api` would all pull the authorisation package in transitively
and the graph would have no direction left. This is why the permission **table**
lives in `core` while the permission **policy** lives in `auth`.

### `infrastructure/` does not know the domain exists

An email transport that reached back into a service would be a circular import
today and an untestable module tomorrow. Adapters are called; they do not call.
Two reach sideways, and neither reaches up: `infrastructure/dkms/blind.py`
normalises a mobile with `validation`'s `normalise_mobile`, so a number has one
keyed hash however it was typed, and `infrastructure/messaging` reads the
office's words from their Redis mirror through `db/redis`.

### `infrastructure/dkms` is called from three layers that otherwise would not

The one deliberate exception to the table's rule, and why it is not a
violation.

**Sealing happens at the repository write.** A repository is the last code
that holds a row before it is bound into SQL, and the only code that sees
every write of a table. So a repository that writes a personal column passes
the row through `seal()` first, and a repository that finds a row by a sealed
value computes the keyed hash (`index_of`) or the n-gram runs (`ngrams_of`,
`search_ngrams`) to compare against. Putting this in the services would mean
every service remembering, on every write; putting it in the repository makes
"personal columns are ciphertext" a property of the structure, the same way
"every write is audited" is. `seal()` is a no-op for a column that is not
personal, so a repository may call it on every write of a table without
deciding which writes matter. One service seals directly: the rights service
seals a respondent's contact into the holder's JSON copy of it, which no
repository writes whole.

**Routers and `auth` use the hash and `opened()`, not the key.** `me.py` and
`users.py` compare a new mobile's keyed hash with the stored one to decide
whether it changed; `registry.py` opens an account to copy its contact to a
respondent; `system.py` asks the key service whether it is up for `/ready`;
the authentication service computes the hash of what was typed at sign-in and
opens the contact a code goes to. None of them decides anything about
encryption.

**Opening is for acting, never for answering.** `opened()` and `unseal*()`
are called only where the backend itself uses a value: the worker sending a
message (`infrastructure/messaging`), a CSV export (`domain/exchange`), an
access response package (`domain/rights/package.py`), a comparison at sign-in.
The API's responses carry the sealed value; the portal's server opens it.

`infrastructure/dkms` imports only `core`, `validation` and its own modules,
so the exception adds no edge back up the graph. The decision is
[ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md).

## Where each kind of check belongs

Three kinds, and keeping them apart is what stops each being done in the wrong
place:

| Kind | Example | Where | Why there |
|---|---|---|---|
| **Shape** | is this a string of ≤200 chars, a uuid, an http URL | Pydantic, at the boundary, from `validation/` | Cheapest, and it never reaches a service |
| **Rule** | may this project move to that state | the domain | Needs the current row to decide |
| **Invariant** | can this row exist at all | the database | Must hold for a write that never saw Python |

The third is the one people skip. A CHECK constraint holds for a migration, a
psql session and a bug — a Python check holds for the code path somebody
remembered.
