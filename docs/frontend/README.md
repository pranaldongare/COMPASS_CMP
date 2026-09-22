# Frontend

What is written about the browser side — the staff console and the
data-principal portal under [`frontend/`](../../frontend/) — beyond how to
run each (that is in each portal's own `README.md`).

- [Best practices](best-practices.md): the engineering standard for React
  and Next.js work here — twenty-four areas, each with the rule, how this
  codebase meets it and where, what it deliberately does differently (client
  rendering behind a first-party proxy, no global store, no Server Actions),
  and what is still open. Ends with the fifteen-question decision matrix a
  pull request answers.

Related, elsewhere in the tree:

- [Repository layout](../architecture/repository-layout.md) — where a file goes
- [ADR 0003](../decisions/0003-server-side-sessions-and-first-party-proxy.md) — why the browser is the only session holder
- [ADR 0009](../decisions/0009-two-portals-by-audience.md) — why there are two portals
- [Proposed repository structure](../architecture/proposed-repository-structure.md) — the `frontend/shared` package still to be built
- [Testing](../operations/testing.md) — the portal unit and browser suites
- [Personal data](../domain/personal-data.md) — what the portals decrypt, and where
