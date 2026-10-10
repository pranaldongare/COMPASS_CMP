# Frontend summary: where the console and portal stand, and how to improve the UI

**Date:** 2026-10-10 · **Compared against:**
[frontend-engineering-roadmap.md](frontend-engineering-roadmap.md)

**What was looked at:** both apps' code (293 `.tsx` files; 41 console pages,
16 portal pages) and screenshots of the running apps at 1440 × 900, signed in
as the DPO, a DCO and a data principal: dashboards, Projects, Consents,
Rights requests, Data sources, My consents and Your rights.

---

## 1. In one paragraph

The engineering underneath is solid: the stack, structure, data layer,
security and testing match or exceed the roadmap. The **look** is where it
falls short. The app reads as a wall of grey text in white boxes: every page
opens with a long legal sentence and a tall filter panel built from the
browser's own dropdowns; tables are wide, wrap their text, and repeat three
text buttons on every row; dashboards are lists of numbers with no visual
summary; and the new blue COMPASS sign-in hands over to an indigo app called
"Consent Management Platform", so the product changes colour and name at the
door. None of this needs a rewrite: it is a design-system and
component-level fix, done in the order in section 5.

---

## 2. Against the roadmap

✅ in place · 🟡 partly · ❌ missing · ➖ not used on purpose

### 2.1 Stack and architecture

| Roadmap item | Status | Notes |
|---|---|---|
| Next.js App Router, React, TypeScript strict | ✅ | Both apps |
| Feature-based structure | ✅ | `features/<feature>/{api,queries,mutations,components}` |
| Typed API client | ✅ | Types generated from the backend's OpenAPI; a contract test checks hand-written types against them |
| Environment config | ✅ | `lib/config`, `.env.example` in both apps |
| Tailwind CSS + CSS variable tokens | ✅ | `styles/tokens.css`, `themes.css`, `bridge.css` |
| Light and dark themes | ✅ | Own `ThemeProvider` (not next-themes) |
| shadcn/ui | ➖ | Own primitives in the same style (`cva`, `clsx`, `tailwind-merge`) |
| Radix UI | 🟡 | Only Dialog and Slot; tabs, menu and collapsible are hand-built |
| Lucide icons | ✅ | |
| Motion for React | ❌ | CSS transitions only |
| React Hook Form + Zod | ✅ | |
| TanStack Query | ✅ | With query-key factory and invalidation |
| Zustand | ➖ | Not needed: server data in TanStack Query, filters in the URL |
| TanStack Table | ➖ | Own `ResourceList` with cursor paging and URL filters |
| Recharts | ➖ | Own light chart components (`StatTile`, `Meter`, `StackedBar`, `BarList`, `Pipeline`) - rarely used on dashboards |

### 2.2 Layout and components

| Roadmap item | Status | Notes |
|---|---|---|
| App shell: header, sidebar, breadcrumbs | ✅ | Collapsible sidebar, mobile drawer, breadcrumbs |
| Command palette / global search | ✅ | "Jump to page… ⌘K" (console only) |
| User and notification menus | ✅ | |
| Cards, badges, alerts, skeletons, empty states | ✅ | |
| Tables with search, filters, pagination | ✅ | No column sorting, no row-action menu, no sticky header |
| Tabs, collapsible cards, dialogs, confirm dialog, menus | ✅ | |
| Accordion | ❌ | |
| Tooltip, Popover, HoverCard | ❌ | |
| Styled Select / Combobox | ❌ | Native `<select>`: looks like the browser, not the product |
| Date picker | ❌ | Native date input (`dd/mm/yyyy`) |
| Switch, styled Checkbox and Radio group | ❌ | Native controls |
| Sheet / side drawer for details | 🟡 | Mobile navigation drawer only |
| Toasts | ✅ | |
| `loading.tsx`, `error.tsx`, `global-error.tsx` | ❌ | Neither app has them; a crash shows Next's default screen |
| Friendly 404 | ✅ | `not-found.tsx` |

### 2.3 Security

| Roadmap item | Status | Notes |
|---|---|---|
| `HttpOnly` session cookies, CSRF token | ✅ | |
| Server-enforced authorisation | ✅ | UI hiding is convenience only |
| MFA for staff | ✅ | |
| CSP with per-request nonce | ✅ | `src/proxy.ts` |
| Security headers | ✅ | `X-Frame-Options: DENY` and others in `next.config.ts` |
| Safe redirects (`next=`) | ✅ | Same-origin paths only |
| `method="post"` on credential forms | ✅ | |
| No personal data in URLs or logs | ✅ | Personal data sealed by a separate key service |
| Dependency audit | 🟡 | Not run routinely |

### 2.4 Accessibility, performance, testing

| Roadmap item | Status | Notes |
|---|---|---|
| Semantic HTML, labels, keyboard, focus | ✅ | Skip link, labelled fields, focus rings |
| Reduced motion | ✅ | `base.css` |
| Lint for accessibility | ✅ | `eslint-plugin-jsx-a11y` |
| Automated axe checks | ❌ | |
| Translations | ❌ | English only (an open decision) |
| Paging of large lists | ✅ | Cursor paging everywhere |
| Image and font optimisation, bundle analysis | 🟡 | No bundle analysis |
| Unit and component tests | ✅ | Vitest: 407 console, 247 portal |
| End-to-end tests | ✅ | Playwright, with screenshot comparisons |
| Lint, format, pre-commit | ✅ | ESLint, Prettier, Husky, lint-staged |

**Bottom line:** the roadmap's engineering items are almost all in place. The
gaps are **UI components** (styled selects, date picker, tooltips, accordion,
row menus), **error and loading pages**, **axe checks** and **motion**, and
those are the same gaps that make the UI look unfinished.

---

## 3. Why the UI looks bad: what the screenshots show

### 3.1 Two brands

- The sign-in screens are the new **blue COMPASS** design. Inside, the header
  says **"Consent Management Platform"** in an **indigo/purple gradient**
  (logo tile, primary buttons, the portal's Your rights banner). The product
  appears to change name and colour after signing in.

### 3.2 Every page starts with too much

- Each page opens with a **long, legal description** ("Access, erasure and
  grievance - sections 11 to 13, and a nominee acting under section 14…"),
  then a **tall filter panel** with labels above full-height controls. The
  data starts a third of the way down the screen.
- Filters use the **browser's native dropdowns and date fields**, which look
  out of place next to the styled inputs and differ between browsers.

### 3.3 Tables are crowded and wrap

- **Data sources** has eight columns; names and processors wrap onto three or
  four lines, and every row repeats **View · Reassign · Edit** as text
  buttons, so the actions column is the widest thing on the page.
- Every name is a **blue link**, every row the same weight: nothing guides the
  eye. No column sorting, no sticky header on long lists, no row hover
  actions.
- Codes such as `RR-2026-018524` and dates repeat on every line in full.

### 3.4 Dashboards are lists, not summaries

- The DPO dashboard is a **list of numbers** ("143 Breach duties overdue",
  "249 outstanding"…) followed by long breach rows. There are no KPI cards,
  no trend, no chart, though chart components exist in the code.
- "Good day, Priya" and the role eyebrow take space without telling the user
  anything.

### 3.5 The portal buries the main content

- **My consents** opens with **dozens of identical notices** ("Ravi Verma
  acted for you on…"), one per request, before any consent appears. A data
  principal never reaches what the page is named after.
- *Your rights* is a long, centred document with a purple banner unlike the
  rest of the portal.

### 3.6 Smaller things

- The sidebar's footer (Collapse sidebar, Sign out) sits on a translucent
  panel that overlaps the last menu items.
- Grey-on-white everywhere: low contrast between page, card and table.
- Large empty margins at wide screens; tables do not use the space well.
- The development data (hundreds of test requests, breaches and processors)
  makes counts and lists look broken. Clean demo data would help every review.

---

## 4. Principles for the redesign

1. **One brand.** COMPASS, in the sign-in blue, from the sign-in screen to
   every page.
2. **Content first.** Title, one short line, then the data. Filters compact
   and collapsible.
3. **Quiet tables.** Fewer columns, truncation with tooltips, one row menu,
   sortable headers.
4. **Summaries before lists.** Dashboards open with KPI cards and a chart.
5. **Styled controls only.** No browser-native dropdowns or date fields.
6. **Hierarchy through weight and colour,** not more text.

---

## 5. Improvement plan, in order

Sizes: **S** ≈ a day, **M** ≈ 2–4 days, **L** ≈ a week.

### Step 1: One brand and colour system (S)

- [ ] Change the primary colour tokens from indigo to the COMPASS blue
      (`#2f72bb`, hover `#255f9f`, dark-mode `#7fb3e8`) in `themes.css`.
- [ ] Solid primary buttons instead of the indigo gradient.
- [ ] Header: the COMPASS logo (shield + wordmark) with the app name under it,
      as on the sign-in screen.
- [ ] Portal *Your rights* banner in the same blue.
- [ ] Slightly darker page background so white cards stand out.

### Step 2: Missing components (M)

- [ ] Styled **Select** and **Combobox** (searchable) on Radix, replacing
      native `<select>` in filters and forms.
- [ ] **Date picker** and **date-range picker**.
- [ ] **Tooltip** and **Popover**.
- [ ] **Row action menu** (⋯) for tables.
- [ ] **Switch**, styled **Checkbox** and **RadioGroup**.
- [ ] **Accordion**.
- [ ] **Sheet** (side panel) for quick record details without leaving the list.

### Step 3: Page header and filters (S)

- [ ] Page descriptions cut to one line; the legal detail moves into the help
      or a tooltip.
- [ ] Filters in one compact row: search box plus filter buttons that open a
      popover; chips show what is applied, with *Clear all*.
- [ ] Primary action stays top right.

### Step 4: Tables (M)

- [ ] Fewer columns by default (for example Data sources: Source, Processor,
      Accountable, Status, ⋯), with column visibility for the rest.
- [ ] Single-line cells with truncation and a tooltip for the full text.
- [ ] One ⋯ menu per row instead of three text buttons; *View* on row click.
- [ ] Sortable headers where the API supports it; sticky header on long lists.
- [ ] Muted secondary text (codes, emails) and relative dates ("2 days ago",
      full date on hover).
- [ ] Optional comfortable / compact density.

### Step 5: Dashboards (M)

- [ ] A row of **KPI cards** at the top (open requests, due this week, open
      breaches, consents this month), each with a small trend.
- [ ] One or two **charts** (requests by status, consents over time) using the
      existing chart components.
- [ ] *Needs attention* grouped by area (Rights, Breaches, Projects) with
      severity colour, not one long list.
- [ ] Shorter greeting; role shown once, in the header.

### Step 6: Portal (S–M)

- [ ] **My consents**: notices collapsed into one summary card ("65 requests
      with the Privacy Office · 12 actions by your nominee", with *View all*);
      consents shown first, as cards with status, project and a clear
      *Withdraw* button.
- [ ] *Your rights*: the four rights as cards with icons, the request form in
      a clear second step.
- [ ] The same blue header and logo as the sign-in screen.

### Step 7: Polish (S–M)

- [ ] Subtle motion: page fade-in, dialog and sheet slide, list item enter
      (Motion for React or CSS), respecting reduced motion.
- [ ] Illustrated empty states on every list.
- [ ] Sidebar footer as a solid block, not overlapping the menu.
- [ ] Consistent spacing scale and max content width on wide screens.

### Step 8: Quality gaps from the roadmap (S)

- [ ] `loading.tsx`, `error.tsx` and `global-error.tsx` in both apps, in the
      new style, with a *Try again* button.
- [ ] axe accessibility checks in the Playwright suite.
- [ ] Refresh the visual baselines once each step lands.

### Step 9: Demo data (S)

- [ ] Clean the development database of test leftovers (183 test processors,
      hundreds of test requests and breaches) or reseed it, so screens show
      realistic volumes during reviews.

---

## 6. What to do first

Steps **1, 3 and 6** give the biggest visible change for the least work: one
brand colour, shorter page headers with compact filters, and a portal that
shows consents first. Steps **2 and 4** (components and tables) are the
largest and change the feel of every list. Step **5** makes the first screen
after sign-in look like a product rather than a report.
