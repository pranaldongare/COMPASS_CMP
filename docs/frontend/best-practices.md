# Frontend best practices — React and Next.js, as this codebase applies them

The two portals under [`frontend/`](../../frontend/) — the staff console and
the data-principal portal — are Next.js 16 / React 19 / TypeScript
applications against one API. This document is the frontend's engineering
standard: the rules a senior or architect-level React engineer is expected to
hold, and for each one what this codebase already does, where, and what it
deliberately does differently. It is written against the code as it stands on
2026-09-22; where a practice is not yet met, it says so under *Open*.

Read it before writing a feature, and use the [decision matrix](#the-decision-matrix)
at the end as the checklist for a pull request.

The rule that governs all the others: **optimise for clear boundaries,
minimal client JavaScript, correct state ownership, predictable data flow,
measurable performance, security, and a codebase another team can extend
safely — not for the number of libraries.**

---

## Contents

1. [Architecture principles](#1-architecture-principles)
2. [Application structure](#2-application-structure)
3. [Component architecture](#3-component-architecture)
4. [State management](#4-state-management)
5. [Rendering: server and client](#5-rendering-server-and-client)
6. [Data fetching and caching](#6-data-fetching-and-caching)
7. [Code splitting, lazy loading, Suspense](#7-code-splitting-lazy-loading-suspense)
8. [Performance](#8-performance)
9. [Security](#9-security)
10. [TypeScript](#10-typescript)
11. [Error handling](#11-error-handling)
12. [Loading states](#12-loading-states)
13. [Forms](#13-forms)
14. [Testing](#14-testing)
15. [Accessibility](#15-accessibility)
16. [Design system and CSS](#16-design-system-and-css)
17. [API contract](#17-api-contract)
18. [Routing](#18-routing)
19. [Observability](#19-observability)
20. [Dependencies](#20-dependencies)
21. [Code quality pipeline](#21-code-quality-pipeline)
22. [Monorepo and shared code](#22-monorepo-and-shared-code)
23. [Not adopted, and why](#23-not-adopted-and-why)
24. [Red flags](#24-red-flags)
25. [The decision matrix](#the-decision-matrix)

---

## 1. Architecture principles

**The rule.** Separation of concerns, single responsibility, composition over
inheritance, dependency inversion, high cohesion and low coupling, DRY, KISS,
YAGNI. Concretely: a feature-based structure with a clear dependency
direction and explicit public boundaries between features.

**Here.** The dependency direction is one-way and written down in
[repository-layout.md](../architecture/repository-layout.md):

```
app/ (routes)  →  features/<area>  →  lib/  →  types/
                        ↓
                  components/ (ui, layout, data-display, forms, security)
```

- `app/` composes; it holds no business logic and no fetch calls.
- A feature exports through its `index.ts` and nothing else
  ([`features/rights/index.ts`](../../frontend/console/src/features/rights/index.ts)
  re-exports `api`, `queries`, `mutations`, `schemas`). Another feature imports
  `@/features/rights`, never `@/features/rights/components/thread`.
- `lib/` knows nothing about any feature. `types/` knows nothing about anything.
- `frontend/` never imports from `backend/`; `console/` and `portal/` never
  import from each other ([ADR 0009](../decisions/0009-two-portals-by-audience.md)).

**Why it is held this way.** Every boundary above is also a *security*
boundary in this product: the API client is the one place credentials and
CSRF travel, the security components are the one place role checks render,
and personal data is opened in one place. A shortcut past a layer is not a
style problem; it is a control that silently stops applying.

## 2. Application structure

**The rule.** Feature-oriented folders. Shared UI primitives separate from
business components. A route layer, a data-access layer, a state layer, a
validation layer, a configuration layer — each in one place.

**Here.** Both portals share the same shape (console shown):

```
frontend/console/src/
  app/                    routes only: (app)/ for the shell, sign-in/, dkms/decrypt/route.ts
  features/<area>/        one folder per business area (17 in the console)
    api.ts                typed functions over the API client — the service layer
    queries.ts            useQuery hooks, keyed from lib/query/keys
    mutations.ts          useMutation hooks, each naming what it invalidates
    schemas.ts            zod schemas mirroring the API's validation
    components/           the feature's own UI
    index.ts              the public surface
  components/
    ui/                   primitives: Button, Card, Field, Input, Table, Skeleton, Badge, Alert, Dialog
    layout/               app-shell, auth-layout
    data-display/         resource-list, activity-feed, audit-link — business-neutral composites
    forms/                shared form pieces
    feedback/             error-boundary
    security/             Can, RequireRole, RequireFullSession, RequireSection, AuthPageGate,
                          RequireAge (portal), session-warning — render-time gates, none of them
                          a security boundary
  providers/              query, auth, theme, toast; the one Providers composition
  lib/
    api/                  the axios client and the four verbs — the only network code
    query/                keys.ts (every query key), options.ts (shared hook types)
    errors/               ApiError and classification
    permissions/          the role matrix mirrored from the API
    security/             public-routes, sanitize, session-timeout
    format/               dates, names, references as a person reads them
    config/               the one read of process.env
    dkms/                 the response walker that opens sealed values
  schemas/                shared zod primitives: contacts, files, security
  styles/                 tokens.css, themes.css, base.css, utilities.css, print.css
  types/                  hand-curated API types + generated api-schema.d.ts
  test/                   MSW server, fixtures
  proxy.ts                CSP nonce and the no-cookie redirect
```

The anti-pattern this avoids is the flat `components/` with `User.tsx`,
`User2.tsx`, `helper.ts`, `finalHelper.ts` — a frontend monolith. Each thing
here has one home; the table in
[repository-layout.md](../architecture/repository-layout.md#where-does-x-go)
says which.

**Rule of placement.** Ask, in order: is it one feature's? → `features/<area>`.
Is it UI with no business meaning? → `components/ui` or `data-display`.
Is it infrastructure every feature needs? → `lib/`. Only then `app/`.

## 3. Component architecture

**The rule.** Small focused components. Presentational components apart from
orchestration. Composition, not configuration props that grow forever.
Compound components where parts belong together. Custom hooks for behaviour.
A component's props are its contract.

**Here.**

- Primitives are compound where the pieces belong together: `Card` /
  `CardHeader` / `CardTitle` / `CardBody`, `Table` / `Th` / `Td` / `Tr`,
  `DescriptionList` / `DescriptionItem`
  ([`components/ui/primitives.tsx`](../../frontend/console/src/components/ui/primitives.tsx)).
- `Field` takes a render function `(props) => <Input {...props} />` so the
  label, hint, error and `aria-describedby` wiring are decided once and every
  input receives them. A form never wires its own accessibility.
- Behaviour lives in hooks, not in JSX: `useProjects()`, `useApprove()`,
  `useDecrypted()`, `useHydrated()`, `useSessionTimeout()`.
- Pages orchestrate: a page under `app/` picks the hooks, renders the list
  primitive, and hands rows to a feature component. It does not compute.

**Senior rule.** A component is UI composition, not your application. If a
file needs a table of contents, it is three components and a hook.

**Bad**

```tsx
function RequestsPage() {
  // 900 lines: fetches, filters, dialogs, table, pagination, audit, decisions
}
```

**Good**

```tsx
export default function RequestsPage() {
  const filters = useListFilters();          // URL state
  const requests = useRequests(filters);     // server state
  return (
    <ResourceList query={requests} filters={<RequestFilters />}>
      {(row) => <RequestRow request={row} />}
    </ResourceList>
  );
}
```

## 4. State management

**The rule.** Put state as close as possible to where it is consumed, in the
right category. Do not put everything in a global store.

| State | Where it lives here |
|---|---|
| Modal open, hover, expanded row | `useState` in the component |
| Search term, filters, page cursor, sort | The URL (`useSearchParams`); bookmarkable, back-button-safe |
| Selected tab | URL when it should survive a reload, local otherwise |
| Form values, dirty, errors | React Hook Form + zod, per form |
| Everything the API knows | TanStack Query — **server state, never copied into a store** |
| Session, role, MFA state | `AuthProvider`, fed by `/auth/me` through the query cache |
| Theme | `ThemeProvider` (a `data-theme` attribute, persisted) |
| Toasts | `ToastProvider` |
| Complex client state | Not needed. There is no Redux or Zustand and none is planned |

Derived state is derived at render (`const outstanding = tickets.filter(...)`),
not stored beside its source. State is normalised by the server's identifiers:
the cache is keyed by uuid ([`lib/query/keys.ts`](../../frontend/console/src/lib/query/keys.ts)),
so one write invalidates every view of the row.

**Context.** Four providers, each a stable cross-cutting concern: query
client, auth, theme, toast. Not a provider per feature, and never a provider
for API data — that is the query cache's job.

**Bad**

```ts
const [state, setState] = useState({ users: [], modal: false, q: "", page: 1, theme: "dark" });
```

Five categories in one object; every keystroke re-renders the table and the
back button does nothing.

## 5. Rendering: server and client

**The rule.** Prefer Server Components for data fetching, static UI, secrets
and SEO; Client Components for interactivity, state, effects, browser APIs.
Do not write `"use client"` at the top of the application.

**Here — a deliberate exception, and why.** Both portals are, past the root
layout, client-rendered applications. `(app)/layout.tsx` is a Client
Component and 125 files carry `"use client"`. This is a decision, not an
omission:

- **Sessions are HttpOnly cookies validated by the API on every request**
  ([ADR 0003](../decisions/0003-server-side-sessions-and-first-party-proxy.md)).
  A Server Component that fetched data would have to forward the cookie to
  the API from the Next server, making the Next process a second
  authenticated client with its own attack surface. The design has exactly
  one place that holds a session — the browser — and one boundary that
  checks it — the API.
- **Personal data is decrypted in the browser, by design.** Every JSON
  response is walked by the API client and sealed values are opened through
  the portal's own `/dkms/decrypt`
  ([personal-data.md](../domain/personal-data.md)). Rendering rows on the
  server would move decryption server-side and defeat the purpose.
- **There is no SEO.** `robots: noindex` on both portals; nothing is public
  content.
- **Every screen is interactive.** Registers, filters, forms, dialogs,
  decisions; there is no static marketing surface.

What *is* server-side, and must stay so: the root layout (metadata,
viewport, the CSP nonce minted per request in [`proxy.ts`](../../frontend/console/src/proxy.ts)),
the `/dkms/decrypt` route handler (server-only `DKMS_URL`, session cookie
required), and the `/api` rewrite that keeps the API first-party.

**Rule for new work.** Do not add server-side data fetching for an
authenticated page. A new Server Component is justified for static,
session-free content only — a public notice viewer would qualify. The
question "server or client?" in the [decision matrix](#the-decision-matrix)
still has to be answered; here the answer is usually "client, and here is
why".

## 6. Data fetching and caching

**The rule.** One data-access layer. Component → hook → service → API client
→ backend. Never `fetch` in `useEffect`. Server state has fetching, caching,
revalidation and retry; client state does not.

**Here.**

```
RequestsPage
   ↓ useRequests(filters)              features/rights/queries.ts
   ↓ listRequests(filters)             features/rights/api.ts
   ↓ apiGet("/requests", { params })   lib/api/client.ts
   ↓ /api/requests  →  rewrite  →  the API
```

- **The client** ([`lib/api/client.ts`](../../frontend/console/src/lib/api/client.ts))
  sets credentials, the CSRF header on unsafe verbs, a request id, normalises
  every failure into `ApiError`, redirects once on 401, and opens sealed
  values. Nothing else in the tree constructs a request.
- **Query keys** are all in one file, grouped by domain with shared prefixes,
  filters last, `as const`, so `invalidateQueries(keys.project.detail(uuid))`
  reaches the detail, its history, its transitions and its sites in one
  call, and a typo is a compile error.
- **Mutations** name what they invalidate, in `mutations.ts`, next to the
  query they affect. The failure mode of a missed invalidation is a screen
  quietly showing the old number, so this is reviewed like a write.
- **Defaults** ([`providers/query-provider.tsx`](../../frontend/console/src/providers/query-provider.tsx)):
  `staleTime` from config; **never retry a 4xx** (a 403 is a 403 on the
  fourth attempt and each attempt is an audited denial); **never retry a
  mutation** (writes go to append-only stores); exponential backoff capped at
  8 s for the rest.
- **Pagination** is cursor-based from the API
  ([api.md](../architecture/api.md#pagination)); the cursor lives in the URL.
- **Deduplication** comes free from the shared cache: ten components asking
  `useMe()` produce one request.
- **Optimistic updates** are used sparingly and only where the write cannot
  be refused for a reason the user did not see — a read-marker, not a state
  transition. A transition the API may reject is shown after the response.

**Caching layers to think about.** Browser → `/api` rewrite (no cache;
`Cache-Control: no-store` on `/c` and `/my-consents`) → TanStack cache
(per-key, `staleTime`) → API. Ask: is it user-specific (always, here)? who
invalidates it? is stale acceptable? Nothing personal is ever cached by an
intermediary.

## 7. Code splitting, lazy loading, Suspense

**The rule.** Route-level splitting by default; component-level `dynamic()`
for heavy, rarely-used client code (charts, editors, PDF viewers, admin-only
tools); Suspense boundaries placed intentionally so independent parts of a
screen load independently. Do not lazy-load what is visible on first paint.

**Here.** Next splits per route automatically, and the shell is shared.
There are no `next/dynamic` imports yet and no `loading.tsx` segments.

**Open.**
- `components/ui/charts.tsx` (the dashboard) and the audit CSV export path
  are the candidates for `dynamic()`; measure first with `next build`'s
  chunk report.
- Dashboard cards should each sit in their own boundary so a slow summary
  does not hold the counts.
- A `loading.tsx` per route group would replace the per-page skeleton
  branch. Not urgent — every list already renders `TableSkeleton` from its
  query state — but it is the framework-native form.

## 8. Performance

**The rule.** Think in four costs — network, server, browser execution, user
experience (LCP, INP, CLS). Measure first, optimise second. Do not sprinkle
`useMemo` / `useCallback` without a measured re-render problem. Never render
ten thousand rows.

**Here.**
- Lists are paginated by the API (default 50, max 200); no page renders an
  unbounded array. Virtualisation is not in use and is not needed at these
  sizes; the audit trail, the one table that could grow, is cursor-paged.
- One decrypt round-trip per response, however many rows — the API client
  batches every sealed value in a body into one `/dkms/decrypt` call.
- No image content to optimise; the portals ship no raster assets.
- Fonts are system stacks (`tokens.css`); nothing is downloaded.
- Playwright's `visual.spec.ts` guards layout shift on the screens that
  matter.

**Open.** There is no bundle analysis in CI and no Web Vitals reporting.
Add `@next/bundle-analyzer` to a `verify:bundle` script and fail on a budget
before adding the first chart library.

**Bad**

```tsx
const rows = useMemo(() => users.filter(f), [users, f]); // on a 20-row list
```

## 9. Security

**The rule.** XSS, CSRF, authentication, authorisation, secure cookies,
token handling, CSP, input validation, dependency security, secrets. The
client is never the security boundary.

**Here** — the frontend half of what [security/](../security/) describes:

| Concern | Where |
|---|---|
| Session | HttpOnly, `SameSite=Lax` cookie set by the API; JavaScript never sees it. `/api` is a same-origin rewrite so the cookie is first-party |
| CSRF | Double-submit: the readable `cmp_csrf` cookie is echoed as a header on every unsafe verb by the API client, once, for everything |
| CSP | Per-request nonce minted in `proxy.ts`; the theme script is the only inline script and carries it |
| Headers | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` (a consent-link URL in a Referer would hand the capability onward), `Permissions-Policy`, COOP |
| Authorisation in the UI | `Can` / `RequireSection` hide what the role may not do — a courtesy; the API enforces on every request and answers 401/403/404 |
| Redirect without a session | `proxy.ts` bounces a cookie-less request to sign-in; it cannot and does not validate the cookie |
| Secrets | None in the client bundle. `DKMS_URL` is read only in the server route handler; `NEXT_PUBLIC_*` carries nothing sensitive |
| Personal data at rest in the browser | Opened values live in the query cache in memory, not in `localStorage`; `no-store` on the pages that show them |
| Input | zod on every form (`features/*/schemas.ts`, `schemas/`); the API validates again and is the authority |
| XSS | No `dangerouslySetInnerHTML` outside the nonce'd theme script. React escapes text nodes; `lib/security/sanitize.ts` covers the places its escaping does not reach — an `href`, a `download` filename, a `window.open` target, a blob URL |
| Dependencies | Gitleaks secret scan in CI; **open:** add `npm audit --omit=dev` per portal to the pipeline beside `pip-audit` |

**Bad**

```ts
const API_KEY = "sk-live-…"; // shipped to every browser
localStorage.setItem("session", token);
```

## 10. TypeScript

**The rule.** `strict`. Typed props. Discriminated unions for state that has
shapes. Generic components where the generic earns its keep. Types for every
API payload. No `any`. Type guards at the untrusted edge; runtime validation
where types vanish.

**Here.**
- `strict: true`; `@typescript-eslint/no-explicit-any` warns and is treated
  as a review blocker.
- The API is typed twice, on purpose: hand-curated types in `types/` that
  read as the domain reads, and `api-schema.d.ts` generated from the running
  API's OpenAPI document. `types/api-contract.test-d.ts` asserts the curated
  types are assignable to the generated ones, so a server change fails
  `npm run api:check` before it fails a user.
- Runtime validation is zod at the two edges where types are only a hope:
  form input (`schemas.ts`) and anything read from the URL or storage.
- Query keys are literal tuples (`as const`); a wrong segment does not
  compile.

**Open.** `noUncheckedIndexedAccess` is off. Turning it on is a
several-hundred-line change and is worth doing in one pass.

## 11. Error handling

**The rule.** Boundaries at the application, route and feature levels, not
one per component. Every error carries a user message, a technical message,
a code, a correlation id, and a recovery. Do not let each component invent
its own.

**Here.**
- One error contract from the API
  ([api.md](../architecture/api.md#errors)): `{ error: { code, message,
  request_id, field?, … } }`. The client turns every failure, including
  network and timeout, into `ApiError` with `isAuthError`, `needsMfa`,
  `isValidation`, `field`, `requestId`
  ([`lib/errors/api-error.ts`](../../frontend/console/src/lib/errors/api-error.ts)).
- A form maps `field` onto its own field error; anything else becomes a
  form-level alert with the request id, so support can find the log line.
- `components/feedback/error-boundary.tsx` wraps the shell in `Providers`;
  a render error shows a recovery screen and reports through
  `console.error` — the one permitted console call.
- 401 is handled once, in the client, by the auth provider's handler; no
  `catch` block redirects.

**Open.** No `app/**/error.tsx` segments yet; the single boundary is the
shell's. Adding route-level `error.tsx` files keeps the navigation usable
when one section fails.

## 12. Loading states

**The rule.** Not `Loading…` everywhere. Skeletons that match the shape,
progressive rendering, empty states that say what to do, and a distinct
error fallback.

**Here.** `Skeleton`, `TableSkeleton` and `EmptyState` are primitives;
`ResourceList` renders the right one from the query's state — loading,
error, empty, rows — so a page never branches on `isLoading` itself. The
empty state names the action ("Register a processor" with the link), not the
absence.

## 13. Forms

**The rule.** Schema validation shared between client and server intent;
client validation for feedback, server validation as the authority; dirty
state; error mapping by field; optimistic UI only where safe.

**Here.** React Hook Form with a zod resolver, one `schemas.ts` per feature
mirroring the API's rules (`ShortText`, `LongText`, `Contact`, `Mobile`
primitives in `schemas/`). A 422 from the API lands on the field it names.
Unsafe verbs carry CSRF automatically. Multipart uploads drop the JSON
content type so the browser sets the boundary. Submit buttons disable during
the mutation; nothing double-submits.

**Never** trust only the client's validation. The API's answer is the
truth; the client's schema exists so the person hears it before the round
trip.

## 14. Testing

**The rule.** A pyramid: unit for logic, component for behaviour,
integration for a feature's workflow, end-to-end for the critical journeys.
Not everything end-to-end.

**Here** ([testing.md](../operations/testing.md)):

| Tier | Tool | What it proves |
|---|---|---|
| Unit | Vitest | error classification, formatting, schemas, the response walker's envelope parsing |
| Component / integration | Vitest + Testing Library + **MSW at the network boundary** | the real axios client, interceptors and query layer run; only the server is fake. A mocked hook proves nothing about the URL, credentials, CSRF or envelope — and those are where the bugs were |
| Contract | `api-contract.test-d.ts` | curated types match the generated OpenAPI schema |
| Sealing | `lib/api/client.test.ts` | a sealed body comes out opened in one decrypt call, nothing else changed |
| End-to-end | Playwright, three projects (desktop, mobile, cookie-domain) | sign-in and MFA, every nav section per role, the rights journeys, the consent flow, detail pages resolve, visual snapshots, and `sealed-never-shown.spec.ts`: the API answered sealed, the page shows the person |
| Accessibility | `eslint-plugin-jsx-a11y` as errors, labels asserted in e2e | |

`onUnhandledRequest: "error"` in the MSW setup: a request no handler covers
fails loudly rather than timing out into "element not found".

## 15. Accessibility

**The rule.** Semantic HTML, keyboard, focus management, ARIA where
semantics run out, screen readers, contrast, accessible forms. Treat it as
architecture.

**Here.** This product is used by people exercising a statutory right; an
unlabelled control is a barrier to it. So: `jsx-a11y` rules are errors, not
warnings; `Field` wires `label`, `aria-describedby` and `aria-invalid` for
every input; dialogs are Radix (focus trap, escape, return focus); tables
use `<table>` with `scope`; status is conveyed by text as well as colour
(`Badge` with `dot` and words); the viewport is not zoom-capped because
someone reading a privacy notice on a phone is exactly who needs to zoom.

**Bad**

```tsx
<div onClick={remove}>Delete</div>
```

Use `<Button>`; the primitive gives you the keyboard.

## 16. Design system and CSS

**The rule.** Tokens → primitives → components → patterns. Typography and
spacing scales. Themes from the same tokens. Variants, not one-off classes.
Avoid global CSS beyond the reset.

**Here.** Tailwind 4 with `@theme` tokens in
[`styles/tokens.css`](../../frontend/console/src/styles/tokens.css): a 1.2
modular type scale, OKLCH colour so dark mode inverts without going muddy,
one spacing scale, radius and shadow steps. `themes.css` maps semantic
names (`bg-surface`, `text-text-muted`, `border-border`) onto the scales for
light and dark; components use the semantic names only. Variants are
`class-variance-authority` on the primitives (`Button variant="primary"
size="sm"`). `print.css` exists because a consent artefact is printed.

**Rule.** No hex in a component. No spacing that is not a step. If a
component needs a colour that has no semantic name, the name is added to
`themes.css` first.

**Open.** No Storybook. The primitives file is small enough to read; revisit
when it is not.

## 17. API contract

**The rule.** One client abstraction; DTO types; runtime validation at the
edge; one error contract; one pagination contract; the backend and frontend
separable.

**Here.** Covered above; the contract is in [api.md](../architecture/api.md)
and regenerated types keep it honest (`npm run api:types` from the running
API). The API is versionless by decision — one deployment ships both — so
compatibility is held by the contract test, not by a version in the path.

## 18. Routing

**The rule.** Route groups for shells, nested layouts, dynamic segments,
middleware for cheap cross-cutting work only, authorisation on the server.

**Here.** `(app)/` is the shell for signed-in staff; `sign-in/` and the
public pages sit outside it. Dynamic segments are uuids (`requests/[uuid]`,
`c/[token]`). `proxy.ts` does two cheap jobs — CSP nonce and the no-cookie
redirect — and explicitly is *not* authorisation. Per-section access is
`RequireSection` at render plus the API's 403; a route is never trusted to be
a permission.

Parallel and intercepting routes are not used; nothing needs them yet.

### Who lands where: the auth routing

Signed-in-ness is decided by the API, answered through `GET /auth/me`, and
read in three places that must agree. None of them is authorisation - every
one of them could be bypassed and the API would still answer 401, 403 or
404 - they only send a person to the page that is theirs.

| Layer | Where | What it does |
|---|---|---|
| No cookie at all | [`proxy.ts`](../../frontend/console/src/proxy.ts) | A request for a non-public path carrying no session cookie is redirected to `/sign-in?next=<path>`. It sees only whether a cookie is present, never whether it is valid. Public paths are one list, `lib/security/public-routes.ts`, shared with the auth provider |
| A protected page | `RequireAuth` in `providers/auth-provider.tsx`, wrapping `(app)/layout.tsx` | Renders nothing until the session resolves, so no page flashes its contents. No session: `/sign-in?next=`. A 401 from any request lands in the same place, through the one handler the provider wires into the API client |
| An auth page | `AuthPageGate` in `components/security/auth-page-gate.tsx` | Sends away the people a sign-in form was not written for, below |
| An unknown age (portal only) | `RequireAge` in `components/security/require-age.tsx`, inside `RequireSection` in `(app)/layout.tsx` | When `me.is_minor` is `null` - the server's "unknown", never "adult" - every page shows the date-of-birth question instead, bar `/my-consents` and `/my-requests`, which stay open with a reminder: withdrawing and making a request are not consents. The answer goes to `PATCH /me` and the session is re-read. The consent-link page asks the same question between the code and the notice. The server is what refuses (`age_required`); this asks at the moment it can be answered (S2-01) |

**Three session states.** `useSessionState()`, in the auth provider, asks
`/auth/me` under the provider's own query key - the provider itself does
not ask on a public path - and answers `none` (no session), `partial`
(password accepted, the staff second factor outstanding: a 401 carrying
`needsMfa`) or `full` (signed in, with the account), plus `loading` while it
asks. The form renders while it asks; it discloses nothing, so there is no
flash to hide.

**On the console**, `AuthPageGate step=…` wraps `/sign-in` (`password`) and
`/sign-in/verify` (`code`):

| Arrives | On `/sign-in` | On `/sign-in/verify` |
|---|---|---|
| `none` | the form | back to `/sign-in`, carrying `?next=` |
| `partial` | on to `/sign-in/verify`, carrying `?next=` | the code form |
| `full`, staff | to `next`, or `/dashboard` | to `next`, or `/dashboard` |
| `full`, data principal | to her portal (`NEXT_PUBLIC_SUBJECT_PORTAL_URL`) | the same |

A `reset` step exists for a reset page and leaves a full session where it
is, since a signed-in person may be finishing a reset from an email;
`/sign-in/reset` does not use the gate today. `RequireAuth` sends a partial
session to `/sign-in/verify?next=`, and shows a data principal who reached
the console with a shared cookie a page saying the console is for staff,
with a link to her portal.

**On the portal**, `AuthPageGate` wraps `/sign-in` and `/sign-up`:

| Arrives | Goes to |
|---|---|
| `none` | the form |
| `full`, data principal | `next`, or `/my-consents` |
| `full`, staff | the console's `/dashboard` (`NEXT_PUBLIC_STAFF_PORTAL_URL`) |
| `partial` | the console's `/sign-in/verify` |

Nobody who belongs on the portal has a password, so it has no code step of
its own - but staff who use both sites type `/sign-in/verify`, bookmark it
and carry it in `?next=`. The portal's `/sign-in/verify` is therefore a
forwarder to the console's, carrying `next`. `RequireAuth` on the portal
sends a partial session there too, and shows a staff account a page saying
the portal is for data principals.

**`next` is a same-origin path or nothing.** Every place that honours it -
the forms and both gates - passes it through `safeRedirectPath` in
`lib/security/sanitize.ts`, which strips invisible characters, accepts a
path beginning `/`, and refuses `//host`, `/\host` and anything with a
scheme, falling back to the default. Leaving for the other portal is always an absolute URL
built from configuration, with `window.location.replace`, because the
router cannot cross origins; `next` never names another origin.

## 19. Observability

**The rule.** Error tracking, performance monitoring, Web Vitals, user
journey tracking, logging, tracing.

**Here.** Every request carries `X-Request-ID`, which the API logs and echoes
in its error body; a user-visible error shows it, so one id joins the
screen, the browser console and the API log. Personal data never enters a
log line on either side.

**Open.** No client error reporter and no Vitals collection. When one is
added, it must scrub as the API's log scrubber does (tokens, contacts,
sealed values) before anything leaves the browser — see
[personal-data.md](../domain/personal-data.md#logs).

## 20. Dependencies

**The rule.** Before adding one: do we need it? can React or an existing
utility do it? bundle size? maintenance? security? licence?

**Here.** The runtime list is fourteen packages and each earns its place:
Next/React, TanStack Query (server state), axios (interceptors), React Hook
Form + zod (forms), Radix dialog and slot (accessible primitives), CVA /
clsx / tailwind-merge (variants), lucide (icons). No state library, no date
library (`Intl` in `lib/format`), no component kit.

## 21. Code quality pipeline

**The rule.** Lint, format, strict types, pre-commit hooks, unit tests,
build checks, dependency scanning, CI.

**Here.** `npm run verify` = typecheck + lint + vitest, the same gate locally
and in CI; Husky + lint-staged run ESLint and Prettier on staged files;
`next build` fails on a type error the dev server tolerates, so it is part
of the gate; CI (`docs/tools/ci.yml.proposed`) runs verify and build per
portal and a secret scan over the whole repository.

## 22. Monorepo and shared code

**The rule.** Shared UI, types and config as packages with enforced
dependency boundaries, when there is more than one application.

**Here.** Two applications, and 65 files byte-identical between them
(`lib/api`, `lib/errors`, `lib/dkms`, `lib/query`, most of `components/ui`,
the error boundary, the MSW setup) plus 37 near-duplicates
([proposed-repository-structure.md](../architecture/proposed-repository-structure.md)).
They are maintained by copying, and the DKMS work this month had to be done
twice.

**Open — the next structural step.** `frontend/shared/` as a workspace
package holding the identical files once, each portal importing
`@compass/shared/*`; the near-duplicates (`config`, `app-shell`,
`auth-provider`) parameterised rather than forked. Turborepo is not needed
for two apps; npm workspaces are enough. The dependency rule stays: a
portal imports `shared`; `shared` imports neither portal.

## 23. Not adopted, and why

| Practice | Decision |
|---|---|
| Server Components for data | Not for authenticated pages — the browser is the only session holder and decryption is client-side by design (§5) |
| Redux / Zustand | No client state complex enough; server state is the cache, UI state is local or URL |
| Server Actions | Writes go through the typed client to the API, which is the authority; a second write path would be a second place for CSRF and validation |
| Micro-frontends / Module Federation | Two deployables split by *audience*, not by team; there is no organisational need |
| i18n framework | Staff console is English; a data principal's notice is served in her language by the API (`notice_language`), which is content, not UI chrome |
| Feature flags | No gradual rollout yet; when needed, flags come from the API's `/meta` so both portals agree |
| ISR / static rendering | Nothing public and cacheable exists |

## 24. Red flags

What a reviewer stops a change for, in the order it matters here:

🔴 A `fetch`/`axios` call outside `lib/api` · a secret or `DKMS_URL` in
client code · personal data written to `localStorage` or a log · a role
check that only exists in the UI · `any` on an API payload · a mutation
without an invalidation · a component over ~250 lines · business logic in
JSX · a `<div onClick>` · a hex colour in a component · a feature importing
another feature's internals

🟠 A new provider · `useEffect` doing what a query hook does · `useMemo` /
`useCallback` without a measured cause · props drilled four levels · a
copy-pasted component · a new dependency without the §20 questions answered
· `"use client"` on a file that has no state, effect or handler

🟡 Abstraction with one caller · optimisation before measurement · a pattern
imported for its own sake

## The decision matrix

Answer these, in order, in the pull request description for any new screen
or feature. Most answers are one line; an answer that is hard to write is the
design problem.

1. **Where does it live?** feature / component / lib — and why not the others.
2. **Server or client?** Here: client, unless it is public and session-free. Say which.
3. **Who owns the state?** The component, the URL, the cache, a provider.
4. **Which category is each piece of state?** local / URL / server / form / global.
5. **How is data fetched?** Which hook, which key, which service function.
6. **What is cached and who invalidates it?** Name the keys the mutation touches.
7. **What renders first?** The skeleton shape; the empty state's action.
8. **What can be lazy?** Or "nothing above the fold".
9. **What can load independently?** Boundaries.
10. **What happens while loading?** Skeleton / disabled / progress.
11. **What happens on failure?** Field error / alert with request id / boundary.
12. **How is it secured?** The API's check it relies on; what the UI merely hides.
13. **How is it tested?** Which tier proves which claim.
14. **How is it observed?** The request id path; what a support engineer sees.
15. **How does it scale?** At 50 rows, at 5,000, across the second portal.

Then the mental model the matrix encodes, from junior to architect: *how do I
build this component* → *how do I build this feature* → *where should this
feature live, how does its state and data flow, and how does it stay
maintainable* → *how does the whole frontend scale across users, features,
teams, deployments and years*. The questions above are the third and fourth
of those, made routine.

---

*Sources: the checklist this document answers was set by the frontend
architecture review of September 2026; the codebase facts were measured
against `frontend/console` and `frontend/portal` on 2026-09-22 — 111 `.tsx`
files, 17 feature modules, 125 client modules, 168 + 127 unit tests, 179 + 50
browser tests.*
