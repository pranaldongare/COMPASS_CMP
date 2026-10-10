# UI implementation plan: bringing the roadmap into the console and portal

**Date:** 2026-10-10 · **Builds on:**
[frontend-engineering-roadmap.md](frontend-engineering-roadmap.md) (what a
good frontend has) and [summary.md](summary.md) (where the two apps stand and
why the UI looks unfinished).

**Goal:** a console and portal that look like one polished product - calm,
modern enterprise SaaS in the COMPASS blue - without changing how anything
works. Every change is visual or structural on the frontend; the API, the
permissions and the data stay as they are.

---

## Progress

| Phase | State (2026-10-10) |
|---|---|
| 0 Preparation | Shared-files list updated. **Not done:** cleaning the development database - waits for a decision |
| 1 Brand and tokens | **Done** - blue accent and neutrals in both themes, Inter self-hosted, solid buttons, 36 px controls, styled native selects |
| 2 Core components | **Partly** - Tooltip, Truncate, Popover, RowActions (Radix), FilterDate, FilterToggle, RouteError/RouteLoading. Still to do: Combobox, date-range picker, Switch, Accordion, Sheet |
| 3 App shell | **Done** - header lockup, solid header and sidebar, 64 px header |
| 4 Page header and filters | **Done** - one-line descriptions (full text on hover), compact filter row; the audit trail keeps its own panel for now |
| 5 Tables | **Partly** - row menus on Data sources, Users, Processors, Purposes, Consent links; names in text colour; truncation with tooltips. Still to do: sticky headers, column visibility, relative dates |
| 6 Dashboards | **Done** - four figures per role, attention beside the charts |
| 7 Detail pages | Not started - already close to the target |
| 8 Portal | Shares phase 1 and the shared components; its own screens not started |
| 9 Polish and quality | **Partly** - error, global-error and loading pages (console); axe checks on 8 screens, all passing |

---

## Contents

1. [The target look](#1-the-target-look)
2. [Ground rules](#2-ground-rules)
3. [Design system v2](#3-design-system-v2)
4. [Libraries to add](#4-libraries-to-add)
5. [Components: new and changed](#5-components-new-and-changed)
6. [App shell](#6-app-shell)
7. [Page patterns](#7-page-patterns)
8. [Screen by screen](#8-screen-by-screen)
9. [Phases, in order](#9-phases-in-order)
10. [Testing and quality](#10-testing-and-quality)
11. [Risks and how they are handled](#11-risks-and-how-they-are-handled)
12. [Roadmap item → where it lands](#12-roadmap-item--where-it-lands)
13. [Definition of done](#13-definition-of-done)

---

## 1. The target look

**In one sentence:** white cards on a soft blue-grey page, one confident blue,
generous but purposeful spacing, quiet tables, and a summary before every list.

| Quality | What it means on screen |
|---|---|
| **One brand** | COMPASS logo and blue from sign-in to every page; no indigo gradient |
| **Calm** | Neutral greys, one accent colour, colour reserved for status and action |
| **Content first** | Title, one line, data. Filters compact; legal detail in help |
| **Clear hierarchy** | Weight, size and colour separate primary from secondary text |
| **Quiet tables** | Few columns, one line per cell, one ⋯ menu per row, sticky header |
| **Summaries** | KPI cards and a chart open every dashboard |
| **Crafted controls** | Styled dropdowns, date pickers, switches, tooltips - nothing that looks like the browser |
| **Alive, not busy** | 150-200 ms transitions on hover, open and enter; nothing that makes the user wait |

Visual references for the feel: Linear, Stripe Dashboard, Vercel, GitHub's
newer screens - clean neutrals, a single accent, dense but readable tables.

---

## 2. Ground rules

1. **Tokens, not values.** Components use design tokens (`--accent`,
   `--surface`, spacing scale). No hex codes in components.
2. **Both apps together.** Anything listed in `frontend/shared-files.txt`
   must stay byte-identical in console and portal; the shared-files test
   enforces it. New shared files (`styles/auth.css`, new `components/ui/*`)
   are added to that list.
3. **No behaviour changes.** Same routes, same API calls, same permissions,
   same URL filter parameters. Server-side authorisation stays the boundary.
4. **Accessible by construction.** Every new control is built on Radix (or a
   native element) and keeps keyboard support, focus rings and labels.
5. **Each phase ships on its own.** After every phase the apps work, all
   tests pass, and the visual baselines are refreshed deliberately.
6. **Dark mode in step.** Every token has its dark value; every screen is
   checked in both themes.
7. **Unchanged constraints:** no application Dockerfile; no plaintext personal
   data; no CSP relaxation (fonts self-hosted, no external CDNs at runtime).

---

## 3. Design system v2

Changes are made in `src/styles/themes.css` and `src/styles/tokens.css`
(shared by both apps). Values below are the light theme; each has a dark
counterpart.

### 3.1 Colour

**Brand blue scale** (replaces the indigo accent and its gradient):

| Token | Light | Dark | Use |
|---|---|---|---|
| `--accent` | `#2f72bb` | `#6aa6e6` | Primary buttons, active nav, links on hover |
| `--accent-hover` | `#255f9f` | `#8bbbef` | Hover |
| `--accent-active` | `#1d4e85` | `#a9cdf3` | Pressed |
| `--accent-subtle` | `#eef5fc` | `#13263d` | Selected row, active nav background |
| `--accent-border` | `#bfd6ef` | `#2a4b70` | Focus and selected borders |
| `--accent-text` | `#1f5c9e` | `#8bbbef` | Links and accent text |
| `--brand-deep` | `#0e3a6b` | `#0b2a4d` | Sign-in panel, portal banners |

**Neutrals:** page `#f5f7fa` (a touch darker than today so white cards lift),
surface `#ffffff`, border `#e3e8ef`, text `#16202c`, muted `#5b6b80`,
subtle `#8593a6`.

**Status** (unchanged hues, softer fills): success green, warning amber,
danger red, info blue - each with `-subtle` fill, `-border` and `-text`.

**Gradients:** removed from buttons and chrome. One gradient remains: the
deep-blue brand panel (sign-in, portal banners).

### 3.2 Typography

- **Font:** Inter, self-hosted with `next/font/local` (variable font in
  `public/fonts/`), so no runtime request leaves the site and the CSP stays
  strict. Fallback stays the system stack, with the Indian-script Noto
  families for names.
- **Scale:** keep the 1.2 scale; page titles `text-2xl` semibold, section
  titles `text-lg` semibold, body `text-sm`, table text `text-sm`, captions
  `text-xs`.
- **Numbers:** `tabular-nums` in tables and KPI figures.
- **Weight rules:** primary cell text medium (500) in `--text`; secondary
  text regular in `--text-muted`; links are text-coloured and turn blue on
  hover - not blue everywhere.

### 3.3 Shape, depth and space

| Token | Value | Use |
|---|---|---|
| Radius sm / md / lg / xl | 6 / 8 / 12 / 16 px | Badges / inputs, buttons / cards / dialogs |
| Shadow xs | `0 1px 2px rgb(16 24 40 / .05)` | Inputs, buttons |
| Shadow sm | `0 1px 3px rgb(16 24 40 / .08), 0 1px 2px rgb(16 24 40 / .04)` | Cards |
| Shadow md | `0 8px 24px rgb(16 24 40 / .10)` | Popovers, menus |
| Shadow lg | `0 20px 48px rgb(16 24 40 / .16)` | Dialogs, sheets |
| Spacing | 4 px base: 4, 8, 12, 16, 20, 24, 32, 40, 48 | Everywhere |
| Content width | max 1440 px, page gutter 32 px (16 px on phones) | Page container |
| Control height | 36 px (default), 32 px (compact), 44 px (auth) | Inputs, selects, buttons |

### 3.4 Motion

| Token | Value | Use |
|---|---|---|
| `--duration-fast` | 120 ms | Hover, press |
| `--duration-base` | 180 ms | Menus, tooltips, tabs |
| `--duration-slow` | 260 ms | Dialogs, sheets, page enter |
| `--ease-out` | `cubic-bezier(.2,.8,.2,1)` | Enter |
| `--ease-in` | `cubic-bezier(.4,0,1,1)` | Exit |

All motion is disabled under `prefers-reduced-motion` (already wired in
`base.css`).

---

## 4. Libraries to add

Small, accessible, tree-shakable. All in both apps' `package.json`.

| Package | For |
|---|---|
| `@radix-ui/react-popover` | Filter popovers, date picker shell |
| `@radix-ui/react-tooltip` | Truncated cells, icon buttons |
| `@radix-ui/react-dropdown-menu` | Row ⋯ menus, header menus (replaces the hand-built menu) |
| `@radix-ui/react-select` | Styled single select in forms |
| `@radix-ui/react-checkbox`, `@radix-ui/react-radio-group`, `@radix-ui/react-switch` | Styled checkbox, radio, switch |
| `@radix-ui/react-accordion` | Accordion (help, FAQ, long detail pages) |
| `cmdk` | Searchable combobox (project, processor, person pickers) and a better ⌘K palette |
| `react-day-picker` + `date-fns` | Date and date-range pickers |
| `motion` (optional) | Page and list transitions beyond CSS |
| `@axe-core/playwright` (dev) | Automated accessibility checks |

**Not added:** shadcn/ui as a package (we already have its pattern - `cva`,
`tailwind-merge`, Radix), TanStack Table (the URL-driven `ResourceList`
stays), Zustand, Recharts (the existing chart components are enough for
KPI sparklines and bars).

---

## 5. Components: new and changed

All in `src/components/ui/` (shared by both apps) unless noted.

### 5.1 New

| Component | File | Notes |
|---|---|---|
| `Tooltip` | `tooltip.tsx` | Radix; 400 ms delay; used by truncated cells and icon buttons |
| `Popover` | `popover.tsx` | Radix; shadow md, radius lg |
| `DropdownMenu` | `dropdown-menu.tsx` | Radix; replaces `menu.tsx` internals, same exports kept as aliases during migration |
| `RowActions` | `row-actions.tsx` | ⋯ button + `DropdownMenu`; items with icon, label, destructive style |
| `Combobox` | `combobox.tsx` | `cmdk` in a `Popover`; search, keyboard, "All …" option; same `value`/`onChange` as `FilterSelect` |
| `DatePicker`, `DateRangePicker` | `date-picker.tsx` | `react-day-picker` in a `Popover`; returns `YYYY-MM-DD` strings as today's inputs do |
| `Checkbox`, `RadioGroup`, `Switch` | `checkbox.tsx`, `radio-group.tsx`, `switch.tsx` | Radix |
| `Accordion` | `accordion.tsx` | Radix; single and multiple |
| `Sheet` | `sheet.tsx` | Radix Dialog from the right, 480 px; quick view of a record |
| `KpiCard` | `kpi-card.tsx` | Label, big figure, delta, sparkline (existing chart primitives), link |
| `PageContainer` | `layout/page-container.tsx` | Max width and gutters |
| `ErrorState`, `LoadingState` | `feedback.tsx` | For `error.tsx`, `loading.tsx` and in-page failures |

### 5.2 Changed

| Component | Change |
|---|---|
| `Button` | Solid blue primary (no gradient), clear secondary (white + border), ghost, destructive; heights 32/36/44; icon-only variant with tooltip |
| `Input`, `Textarea` | 36 px, radius md, shadow xs, focus ring `--accent-border` + 3 px soft ring |
| `Select` (native) | `appearance-none` with a custom chevron, same height and border as `Input`. Native stays for accessibility and tests; looks like the product |
| `Card` | Radius lg, shadow sm, 20 px padding, optional header actions |
| `Badge` / `StatusBadge` | Radius full, 22 px tall, subtle fill + text colour; dot optional |
| `Table` | Header `text-xs` uppercase muted on `--bg-subtle`, sticky; rows 52 px (44 compact); hover `--surface-hover`; single-line cells with `truncate` + `Tooltip` |
| `Tabs` | Underline style with animated indicator |
| `EmptyState` | Illustration, title, one line, primary action |
| `Skeleton` | Shimmer matched to the real row and card shapes |
| `Dialog` | Radius xl, shadow lg, scale+fade enter |

---

## 6. App shell

Files: `components/layout/app-shell.tsx`, `nav.ts`, `user-menu.tsx`,
`command-palette.tsx`.

**Header (64 px, white, bottom border):**

- Left: COMPASS logo (shield + two-tone wordmark) with the app name small
  under it - the same lockup as sign-in. Then breadcrumbs.
- Centre/right: ⌘K search field (console), help, notifications bell with a
  count dot, user button (avatar, name, role chip) opening the user menu.

**Sidebar (264 px; 72 px collapsed):**

- Groups with small muted labels; items 36 px, icon 18 px, radius md.
- Active item: `--accent-subtle` fill, `--accent-text` text, 3 px blue bar
  on the left.
- Count badges right-aligned, blue for "needs you", grey for totals.
- Footer as a **solid** block (no translucent overlay): collapse toggle and
  sign out, separated by a border.
- Collapsed mode shows icons with tooltips.

**Mobile:** header with menu button; sidebar as a left sheet; content
gutters 16 px.

---

## 7. Page patterns

Every list page uses the same skeleton:

```text
┌───────────────────────────────────────────────────────────────┐
│ Title                                         [Secondary] [+ Primary] │
│ One short line about the page.                                │
├───────────────────────────────────────────────────────────────┤
│ [🔍 Search…]  [Project ▾] [Status ▾] [More filters]   Clear all │
│ chips: Project: Gait Study ×   Status: Partial ×              │
├───────────────────────────────────────────────────────────────┤
│ TABLE (sticky header, ⋯ per row, row click opens the record)  │
├───────────────────────────────────────────────────────────────┤
│ 1–25 of 312                                  ‹ Prev  Next ›   │
└───────────────────────────────────────────────────────────────┘
```

### 7.1 Page header (`PageHeader`)

- Title + **one line** (max ~90 characters). The longer legal explanation
  moves to the page's help topic, reachable from the header's help icon.
- Primary action top right, solid blue; at most one secondary.

### 7.2 Filter bar (`FilterBar`, `FilterSelect`, `SearchBox`)

- One row, 36 px controls, no labels above (labels become the control's
  placeholder text and its accessible name).
- Pickers with many options (project, processor, person) become `Combobox`;
  short fixed lists stay styled native selects.
- Date filters become `DateRangePicker` ("Given: 1–10 Oct").
- Toggles ("Nobody accountable") become chip buttons.
- Applied filters show as removable chips; *Clear all* on the right.
- URL parameters unchanged, so links and bookmarks keep working.

### 7.3 Tables (`ResourceList`)

- Default columns cut to what identifies the row and its state; the rest in a
  column-visibility menu (remembered per user in `localStorage`).
- Primary cell: name in medium weight + one muted line (code or email).
- Secondary values muted; codes in mono `text-xs`.
- Dates as relative ("2 days ago") with the full date in a tooltip.
- Actions: row click opens the record; ⋯ menu holds the rest (View, Edit,
  Reassign, Suspend…). No row of text buttons.
- Sticky header; zebra-free; hover highlight; selected row in accent-subtle.
- Paging footer: "1–25 of 312" with Prev / Next.

### 7.4 Detail pages

- Header: title, status badge, key facts as a row of small labelled values,
  actions top right.
- Body: two columns on wide screens - main content (cards, tabs) and a
  right rail (people, dates, related links, audit trail link).
- Long sections in `Accordion` or tabs.

### 7.5 Forms and dialogs

- Labels above fields, 16 px between fields, two columns where fields pair
  naturally.
- Dialog footers: secondary left of primary, primary on the right.
- Quick record views in a `Sheet` from lists where a full page is not needed.

---

## 8. Screen by screen

### 8.1 Console

| Screen | Change |
|---|---|
| **Dashboards (all roles)** | Row of 4 `KpiCard`s (per role: e.g. DPO - open requests, due in 7 days, open breaches, projects awaiting approval); one chart card (requests by status / consents over 30 days); *Needs attention* grouped by area with severity colour, max 5 per group + "View all"; greeting reduced to the title |
| **Projects** | Columns: Project (name + code), Status, Owner, Updated; ⋯ menu; status filter as chips |
| **Project detail** | Header with progress steps; tabs unchanged; *At a glance* as KPI cards; right rail with owner, dates, audit link |
| **Consents** | Columns: Person (name + email), Project · Site, Status, Purposes, Given; date-range picker; project/site as comboboxes |
| **Rights requests** | Columns: Reference + person, Kind, Status, Due (with progress bar of the 90-day clock); "unverified" as a badge, not floating text |
| **Request detail** | Timeline of the request on the right rail; holders as cards |
| **Breaches** | Board-style status columns optional; duty clocks as progress bars |
| **Data sources** | Columns: Source (name + code), Processor, Accountable, Status, ⋯; authoritative fields in a tooltip / detail |
| **Processors, Users, Purposes** | Same table pattern; avatars for people |
| **Message templates** | Categories as a left list (sticky), templates as cards; search on top - building on the filters added 2026-10-09 |
| **Audit trail** | Monospace event codes muted; actor + entity as the primary line; row opens a sheet with the detail |
| **My tasks** | Cards per ticket with due chip and one primary action |

### 8.2 Portal

| Screen | Change |
|---|---|
| **My consents** | Notices collapsed into one summary card with "View all"; consents first, as cards: project, organisation, status, purposes agreed, date, *Withdraw* button |
| **Consent detail** | Purposes as a checklist with switches for partial withdrawal; notice text in an accordion |
| **My requests** | Cards with status stepper (Received → Verified → In progress → Answered) |
| **Your rights** | Hero in the brand deep blue; four rights as icon cards; request form as a clear second step |
| **Account** | Contacts as a list with verified badges; actions in ⋯ |
| **Consent link journey** | Same brand header; progress steps (Verify → Read → Choose → Done); large touch targets |

---

## 9. Phases, in order

Each phase is one or more commits, ends with all tests green and visual
baselines refreshed. Sizes: S ≈ 1 day, M ≈ 2-4 days, L ≈ a week.

### Phase 0: Preparation (S)

- [ ] Reseed or clean the development database so screens show realistic
      volumes (removes the 183 test processors and test request floods).
- [ ] Capture "before" screenshots of the 15 key screens for comparison.
- [ ] Add new shared files to `frontend/shared-files.txt`.

### Phase 1: Brand and tokens (S)

- [ ] Blue accent scale and neutrals in `themes.css` (light + dark); remove
      the indigo gradient from buttons and chrome.
- [ ] Inter, self-hosted; tabular numbers.
- [ ] Radius, shadow, motion tokens in `tokens.css`.
- [ ] `Button`, `Input`, styled native `Select`, `Card`, `Badge` restyled.
- [ ] Header logo lockup = sign-in lockup.
- **Done when:** every screen is blue COMPASS, no gradient buttons, both
  themes checked.

### Phase 2: Core components (M)

- [ ] `Tooltip`, `Popover`, `DropdownMenu`, `RowActions`.
- [ ] `Combobox`, `DatePicker`, `DateRangePicker`.
- [ ] `Checkbox`, `RadioGroup`, `Switch`, `Accordion`, `Sheet`.
- [ ] `KpiCard`, `PageContainer`, `ErrorState`, `LoadingState`.
- [ ] Unit tests for each (keyboard, ARIA, value contract).
- **Done when:** a component gallery page (development only) shows every
  component in both themes.

### Phase 3: App shell (S)

- [ ] Header and sidebar to the spec in section 6; solid sidebar footer.
- [ ] Collapsed sidebar with tooltips; mobile sheet.
- **Done when:** navigation looks and behaves the same in both apps and on a
  phone.

### Phase 4: Page header and filters (M)

- [ ] One-line descriptions on every page (legal detail moved to help).
- [ ] Filter bar v2: one row, comboboxes, date ranges, chips, *Clear all*.
- [ ] Applied across all list pages (about 20 in the console, 4 in the
      portal).
- **Done when:** data starts in the top third of the screen on every list.

### Phase 5: Tables (M-L)

- [ ] `ResourceList` v2: sticky header, single-line cells with tooltips,
      relative dates, column visibility, ⋯ row menu, row click to open.
- [ ] Each list's columns reduced per section 8.1.
- **Done when:** no table wraps on a 1440 px screen and no row shows more
  than one visible action.

### Phase 6: Dashboards (M)

- [ ] KPI cards and one chart per role dashboard.
- [ ] *Needs attention* grouped with "View all".
- **Done when:** each dashboard's first screen summarises the role's work
  without scrolling.

### Phase 7: Detail pages (M)

- [ ] Header with key facts; two-column layout with right rail.
- [ ] Accordions for long sections; sheets for quick views from lists.

### Phase 8: Portal (M)

- [ ] My consents, consent detail, my requests, your rights, account and
      consent-link journey to section 8.2.
- **Done when:** a data principal sees their consents first, on phone and
  desktop.

### Phase 9: Polish and quality (S-M)

- [ ] Motion tokens applied: dialog/sheet/menu enter, page fade, list enter.
- [ ] Illustrated empty states everywhere.
- [ ] `loading.tsx`, `error.tsx`, `global-error.tsx` in both apps.
- [ ] axe checks in Playwright for the key screens.
- [ ] Final pass in dark mode and at 390 / 768 / 1440 px.

**Suggested order of delivery:** 0 → 1 → 3 → 4 → 2 (components as phases 4-5
need them) → 5 → 6 → 8 → 7 → 9. Phases 1, 3 and 4 alone change the feel of
every screen within about a week.

---

## 10. Testing and quality

| Area | How |
|---|---|
| Unit / component | Vitest + Testing Library for every new component; existing page tests updated where markup changes |
| Selects in tests | Styled native selects keep `user.selectOptions` working; pages moved to `Combobox` get tests that type and pick an option |
| End to end | Playwright suites run after each phase; selectors by role and label, so restyling rarely breaks them |
| Visual regression | Baselines refreshed per phase, reviewed image by image before committing |
| Accessibility | axe on the key screens; manual keyboard pass per phase |
| Shared files | `shared-files.test.ts` keeps both apps' shared components identical |
| Themes and sizes | Every phase checked in light and dark, at 390, 768 and 1440 px |

---

## 11. Risks and how they are handled

| Risk | Handling |
|---|---|
| Restyling breaks many page tests | Keep native `<select>` where a styled one suffices; query by role/label; migrate tests in the same commit |
| Visual baselines churn | Refresh only at the end of a phase, after review |
| Two apps drift apart | All new UI components are shared files, checked by test |
| New libraries widen the CSP | Self-hosted font; Radix, cmdk and day-picker need no external requests |
| Performance regressions | Radix and cmdk are small and tree-shaken; `motion` optional; measure with Lighthouse before and after |
| Scope creep into behaviour | Rule 3: no API, route or permission change; anything else is a separate request |
| Dark mode left behind | Every token has a dark value; review checklist includes dark |

---

## 12. Roadmap item → where it lands

| Roadmap section | Lands in |
|---|---|
| Design system and styling (§5) | Phase 1, section 3 |
| UI component catalogue (§6) | Phase 2, section 5 |
| Layout and navigation (Phase 7 of the roadmap) | Phase 3, section 6 |
| Feature pages and empty/loading/error states | Phases 4-8, section 8 |
| API and state (§8) | Unchanged - already in place |
| Security (§9) | Unchanged; CSP kept strict by self-hosting fonts |
| Accessibility (§10) | Radix components, axe checks (Phase 9) |
| Performance (§11) | Lighthouse before/after; optional `motion` |
| Testing (§12) | Section 10 |
| Release checklist (§13) | Section 13 |

---

## 13. Definition of done

- [ ] COMPASS blue and logo on every screen of both apps; no indigo
      gradient left
- [ ] Every list: one-line header, one-row filters with chips, quiet table
      with ⋯ menus, no wrapping at 1440 px
- [ ] Every dashboard: KPI cards and a chart above the fold
- [ ] Portal: consents first; notices summarised
- [ ] No browser-native dropdown or date field visible in filters
- [ ] Loading, error and empty states designed everywhere
- [ ] Light and dark themes; 390 / 768 / 1440 px checked
- [ ] Unit, end-to-end, axe and visual tests pass; shared-files test passes
- [ ] No change to API calls, routes, permissions or URL parameters
