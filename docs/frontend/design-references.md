# Design references: Dribbble "Software UI"

**Source:** [dribbble.com/tags/software-ui](https://dribbble.com/tags/software-ui),
read 2026-10-10 (the 25 shots on the first page). **Used by:**
[implementation-plan.md](implementation-plan.md).

**About the images.** Every design below belongs to its designer. The images
are shown from Dribbble's own servers and are **not copied into this
repository**: each is credited, and its title links to the original shot,
where the full work, its licence and its author are. If a picture does not
load (offline, or the designer removed it), the link still says what it was.
Nothing here is to be copied as-is; the notes say what *pattern* to take, in
COMPASS's own blue and components.

**Offline copies.** The same 25 images are saved, numbered as in the source
page, in `docs/frontend/design-references/` on the machine that pulled them
(for example `24-azmir-sheikh-risk-assessment.png`). That folder is in
`.gitignore`: this repository is public, and the images are not ours to
republish. Anyone else can pull their own copy from the links below.

---

## Contents

1. [What the best of them share](#1-what-the-best-of-them-share)
2. [Dashboards, tables and app screens](#2-dashboards-tables-and-app-screens) - most useful for the console
3. [Tools and editors](#3-tools-and-editors)
4. [Marketing, branding and pricing](#4-marketing-branding-and-pricing) - for a public site, not the console
5. [From reference to COMPASS](#5-from-reference-to-compass)

---

## 1. What the best of them share

From the app screens in section 2 (the risk register, the ERP receivables,
the guest list, the promotions list and the healthcare dashboard):

| Pattern | What it looks like | COMPASS today |
|---|---|---|
| **Page on a soft grey, content in white panels** | A light grey canvas; the sidebar and the main area are white rounded panels | Done (Phase 1) |
| **Title + one line + one primary action** | "Accounts Receivables" with *Import/Export* and one dark primary button top right | Done (one-line descriptions) |
| **KPI cards with a sparkline** | Three or four cards: label, big number, a small trend line, "last 365 days" | KPI cards done; sparklines not yet |
| **A chart above the table** | A wide line or bar chart with a legend of colour dots, then the list | Dashboard only |
| **Compact filter row** | *Status: All ▾*, *Monthly ▾*, a filter-icon button, search on the right, *Export PDF / Excel* | Compact row done; export buttons per page vary |
| **Segmented tabs inside a page** | Overview · Check List · Consent · Risk Assessment … as pill tabs under the title | Underline tabs |
| **Quiet tables** | Checkbox column, light header, one line per row, coloured status pills, `⋯` row menu | Done for five registers; no checkboxes yet |
| **Row menu with a destructive item** | `⋯` opens *Edit · Delete · Control* | Done (`RowActions`) |
| **Numbered pagination** | *Previous 1 2 … 10 11 12 Next*, plus "Showing 1-10 from 56" | Previous / Next only |
| **People with avatars** | An avatar or initials chip before each name | Not yet |
| **Sidebar with sections and a user card** | Grouped menu, collapsible groups, the signed-in person at the bottom | Groups done; user is in the header |
| **"Recent activity" rail** | A right-hand list of events with icons and relative times ("2h ago") | Activity feed exists; not on the dashboard rail |
| **Insight / alert card** | One coloured card that calls out the single thing to look at | Not yet |
| **Severity colours used sparingly** | High (red), Medium (green/amber), Low (outline) only on the pill | Status pills match |

---

## 2. Dashboards, tables and app screens

### Software design - Risk Assessment

[![Software design - Risk Assessment](https://cdn.dribbble.com/userupload/45871288/file/473b78e26ceab221d541ae3cc897cdbb.png?resize=640x&vertical=center)](https://dribbble.com/shots/26825997-Software-design-Risk-Assessment)

**By** [Azmir Sheikh](https://dribbble.com/uiazmir13) ·
[view on Dribbble](https://dribbble.com/shots/26825997-Software-design-Risk-Assessment)

**Take for COMPASS** - the closest match to our domain:
- A person's record with **tabs across the top** (Overview, Check List,
  **Consent**, Support Plan, **Risk Assessment**, Meeting Notes, Files): the
  shape for a request, breach or consent record.
- A **risk register table**: residual risk as a small coloured pill
  (High / Medium / Low), last and next review dates, sortable headers (↓↑).
- `⋯` row menu with Edit, a greyed Delete and Control.
- Footer "Showing 1-10 from 56" with *Previous / Next*.
- Primary action dark and solid (*+ Participants*), secondary actions outlined
  (*Upload file*, *+ Add New Risk*).

→ Breach detail (risk and duties), request detail tabs, Phase 5 tables.

### Dashboard UI (ERP - Accounts Receivables)

[![Dashboard UI](https://cdn.dribbble.com/userupload/46424984/file/a25d666d0072302abb84984ee149a8c8.png?resize=640x&vertical=center)](https://dribbble.com/shots/26994786-Dashboard-UI)

**By** [Azmir Sheikh](https://dribbble.com/uiazmir13) ·
[view on Dribbble](https://dribbble.com/shots/26994786-Dashboard-UI)

**Take for COMPASS:**
- **Chart card above the table** with a legend of coloured dots and values
  (0-30, 31-60, 61-90 …): exactly the shape for *requests by age against the
  90-day clock*.
- Table toolbar: **Status: All Invoice ▾** select, search, *Filters* button.
- Party column: **initials chip + name + email** on two lines.
- Header: breadcrumb trail, ⌘F search, a task counter, theme toggle,
  notifications with a dot.
- Sidebar: collapsible groups (Accounting ▸ Payables, Receivables …) and the
  user card at the bottom.
- Numbered pagination.

→ Rights requests list (chart of ages), Phase 5 pagination and avatars.

### Hotel Guest List UI - SaaS Software

[![Hotel Guest List UI - SaaS Software](https://cdn.dribbble.com/userupload/18083360/file/original-2b3a5855cfe5092617978c64005b58f2.jpg?resize=640x&vertical=center)](https://dribbble.com/shots/25358841-Hotel-Guest-List-UI-SaaS-Software)

**By** [Fixoria Studio](https://dribbble.com/fixoriastudio) (designer: Salim Era) ·
[view on Dribbble](https://dribbble.com/shots/25358841-Hotel-Guest-List-UI-SaaS-Software)

**Take for COMPASS:**
- **Page icon tile + title + "Auto-updates in 2 min"** - a small freshness
  line under the title.
- Filters as **chip dropdowns** (*All Staff ▾ · Status ▾ · Monthly ▾*) plus a
  filter-icon button; **Export PDF / Export Excel** on the right.
- Guest name in a **pill with an avatar**; status pills in two colours
  (*Paid* green, *Pending* amber).
- Sub-navigation in the sidebar indented under its parent (Manage Guests ▸
  Guests List, Guests Reviews).
- Notifications count in the sidebar footer.

→ Consents and Users lists (person pills), export buttons on registers.

### SaaS Software - Promotions UI

[![SaaS Software - Promotions UI](https://cdn.dribbble.com/userupload/18083296/file/original-87f650d90c5b9cd4f2d6ba5ea7c04f9e.jpg?resize=640x&vertical=center)](https://dribbble.com/shots/25358817-SaaS-Software-Promotions-UI)

**By** [Fixoria Studio](https://dribbble.com/fixoriastudio) (designer: Salim Era) ·
[view on Dribbble](https://dribbble.com/shots/25358817-SaaS-Software-Promotions-UI)

**Take for COMPASS:**
- **Three KPI cards with a sparkline** each (Total, Revenue, Engagement rate,
  "last 365 days").
- **Segmented tabs** for the list's state (*Active · Upcoming · Ended*)
  instead of a status dropdown.
- Status pills *Active Now* / *Ending Soon*.

→ Dashboard KPI sparklines; status tabs on Projects, Notices, Breaches.

### Healthcare Dashboard Web App - Lably

[![Healthcare Dashboard Web App - Lably](https://cdn.dribbble.com/userupload/48890103/file/still-c7c4d757703f3a76e6725ecfef41bfe7.png?resize=640x&vertical=center)](https://dribbble.com/shots/27695351-Healthcare-Dashboard-Web-App-Lably)

**By** [Phenomenon Studio](https://dribbble.com/phenomenonstudio) ·
[view on Dribbble](https://dribbble.com/shots/27695351-Healthcare-Dashboard-Web-App-Lably)

**Take for COMPASS** - a sensitive-data dashboard done calmly:
- Greeting + one line, a **period picker (*This week ▾*)** and one dark
  primary action.
- Four **KPI cards with an icon in the corner**, the alarming one in red
  (*Attention flags*).
- **"Requiring review" carousel** of cards, each a person, a value and a date
  chip: the shape for *requests due soon*.
- **Recent activity rail** on the right with "2 critical" in red and relative
  times.
- One **insight card** in the brand colour.

→ DPO dashboard: due-soon cards, activity rail, one insight card.

### Golf Dashboard Design | Athlete Analytics

[![Golf Dashboard Design](https://cdn.dribbble.com/userupload/43196732/file/original-0042b2c745c4a5dd661dca551ffccbe7.jpg?resize=640x&vertical=center)](https://dribbble.com/shots/25987491-Golf-Dashboard-Design-Athlete-Analytics-Dashboard-UI-UX)

**By** [Musemind](https://dribbble.com/musemindagency) ·
[view on Dribbble](https://dribbble.com/shots/25987491-Golf-Dashboard-Design-Athlete-Analytics-Dashboard-UI-UX)

**Take for COMPASS:**
- **List-detail layout**: a searchable list of people on the left (avatar,
  name, a small tag), the selected one opens on the right without leaving the
  page.
- **Icon-only sidebar** rail.

→ Message templates and My tasks (list on the left, detail on the right).

### Web App Design for Robot Builder - Kinetiq

[![Web App Design for Robot Builder - Kinetiq](https://cdn.dribbble.com/userupload/49060028/file/ed8b14c74eb3c6630550bd0c2ddb42b6.png?resize=640x&vertical=center)](https://dribbble.com/shots/27741608-Web-App-Design-for-Robot-Builder-Kinetiq)

**By** [Phenomenon Studio](https://dribbble.com/phenomenonstudio) ·
[view on Dribbble](https://dribbble.com/shots/27741608-Web-App-Design-for-Robot-Builder-Kinetiq)

**Take for COMPASS:**
- **Three-column workspace**: components on the left in collapsible groups
  with counts (*Head [3]*), the work in the middle, checks on the right with
  *OK* states.
- **Pill tab bar centred in the header** (Overview · Builder · Behaviour ·
  Simulation · Logs History).
- A **compatibility checklist** with green OKs: the shape for "What happens
  next" and readiness on a project.

→ Project detail (readiness checklist), notice editor.

### Enterprise Software Onboarding Web App - ZeBeyond

[![Enterprise Software Onboarding Web App - ZeBeyond](https://cdn.dribbble.com/userupload/49016655/file/dd22ea99057b8584c444d46461690aa9.png?resize=640x&vertical=center)](https://dribbble.com/shots/27729741-Enterprise-Software-Onboarding-Web-App-ZeBeyond)

**By** [Phenomenon Studio](https://dribbble.com/phenomenonstudio) ·
[view on Dribbble](https://dribbble.com/shots/27729741-Enterprise-Software-Onboarding-Web-App-ZeBeyond)

**Take for COMPASS:** a focused **message card** with a headline, three
check-marked benefits and one full-width action, for empty states and
"what this is for" panels.

### Engineering Software Web App Design - ZeBeyond

[![Engineering Software Web App Design - ZeBeyond](https://cdn.dribbble.com/userupload/48542596/file/1d7d39b7adbe2cf0bea6486a72bf6344.png?resize=640x&vertical=center)](https://dribbble.com/shots/27602379-Engineering-Software-Web-App-Design-ZeBeyond)

**By** [Phenomenon Studio](https://dribbble.com/phenomenonstudio) ·
[view on Dribbble](https://dribbble.com/shots/27602379-Engineering-Software-Web-App-Design-ZeBeyond)

**Take for COMPASS:**
- **A stepper form with a live summary**: questions on the left as **chip
  choices** (*Just me · 2-3 people · 4+ people*), a summary card on the right
  that updates as you answer, and a step indicator (*Step 3 of 3*) at the top.

→ Log an incident, Register a project, the portal's rights request form.

### RoomSketch - Interior Design SaaS Web App

[![RoomSketch - Interior Design SaaS Web App](https://cdn.dribbble.com/userupload/44902380/file/still-5ff75879382772e8299e53573cdd681c.png?resize=640x&vertical=center)](https://dribbble.com/shots/26523370-RoomSketch-Interior-Design-SaaS-Web-App)

**By** [Phenomenon Studio](https://dribbble.com/phenomenonstudio) ·
[view on Dribbble](https://dribbble.com/shots/26523370-RoomSketch-Interior-Design-SaaS-Web-App)

**Take for COMPASS:** floating **popover cards** anchored to a point, with an
image, a title, a short line and two actions: the shape for a quick preview
of a record from a list.

---

## 3. Tools and editors

Less about our screens, useful for detail: panels, toolbars and dark mode.

### Developer Tools - AI Assistant Code editor software design

[![Developer Tools - AI Assistant Code editor](https://cdn.dribbble.com/userupload/45500370/file/still-5ad48b6c396ff2a3dc50c5b84b0bbe5c.png?resize=640x&vertical=center)](https://dribbble.com/shots/26708953-Developer-Tools-AI-Assistant-Code-editor-software-design)

**By** [Musemind](https://dribbble.com/musemindagency) ·
[view on Dribbble](https://dribbble.com/shots/26708953-Developer-Tools-AI-Assistant-Code-editor-software-design)

**Take:** a **well-balanced dark theme** (near-black panels, one blue accent,
muted borders) and a three-pane layout with a segmented *Preview · Design ·
Code* switch in the header. A reference for checking our dark mode.

A second shot from the same series:
[![Developer Tools - AI Assistant Code editor (2)](https://cdn.dribbble.com/userupload/45477843/file/still-340d2b87de563125e777cead07454545.png?resize=480x&vertical=center)](https://dribbble.com/shots/26701814-Developer-Tools-AI-Assistant-Code-editor-software-design)
— [Musemind](https://dribbble.com/musemindagency)

### AI Coding Agent | AI Code Editor/Generator | Dark Mode IDE

[![AI Coding Agent](https://cdn.dribbble.com/userupload/46744278/file/still-b8370c9a97713103e12face0e959d16f.png?resize=480x&vertical=center)](https://dribbble.com/shots/27088824-AI-Coding-Agent-AI-Code-Editor-Generator-Dark-Mode-IDE-UI-UX)

**By** [Nasir Uddin](https://dribbble.com/N_udddin) ·
[view on Dribbble](https://dribbble.com/shots/27088824-AI-Coding-Agent-AI-Code-Editor-Generator-Dark-Mode-IDE-UI-UX)

### Collaborative Photo Editing Software UI

[![Collaborative Photo Editing Software UI](https://cdn.dribbble.com/userupload/4239643/file/original-422d819ca1bfe1e33c4bb4db09fdbc0b.jpg?resize=640x&vertical=center)](https://dribbble.com/shots/20268513-Collaborative-Photo-Editing-Software-UI)

**By** [Awsmd](https://dribbble.com/awsmd) ·
[view on Dribbble](https://dribbble.com/shots/20268513-Collaborative-Photo-Editing-Software-UI)

**Take:** a **context menu on the item** (*Duplicate · Reset settings ·
Delete* in red), labelled sliders with their value in a small box, and
*Cancel* (outline) beside *Save* (solid).

### Photo Editor Adjustments - Controller Panel

[![Photo Editor Adjustments - Controller Panel](https://cdn.dribbble.com/userupload/10800646/file/original-89620b8357ae4a7abde37fa3a314dce4.jpg?resize=480x&vertical=center)](https://dribbble.com/shots/22834375-Photo-Editor-Adjustments-Controller-Panel)

**By** [Yasir Ekinci](https://dribbble.com/yasirekinci) ·
[view on Dribbble](https://dribbble.com/shots/22834375-Photo-Editor-Adjustments-Controller-Panel)

### Atlantis AR: 3D Editor (two shots)

[![Atlantis AR: 3D Editor](https://cdn.dribbble.com/userupload/11152894/file/original-1be7ca962a495e8d5b06c5f27f08471b.jpg?resize=480x&vertical=center)](https://dribbble.com/shots/22964380-Atlantis-AR-3D-Editor)
[![Atlantis AR: 3D Editor (2)](https://cdn.dribbble.com/userupload/10874396/file/original-1001781c93def9670910253150a4dcf7.png?resize=480x&vertical=center)](https://dribbble.com/shots/22862181-Atlantis-AR-3D-Editor)

**By** [Flatonica](https://dribbble.com/flatonica) (designer: Vlad Goncharov) ·
[shot 1](https://dribbble.com/shots/22964380-Atlantis-AR-3D-Editor) ·
[shot 2](https://dribbble.com/shots/22862181-Atlantis-AR-3D-Editor)

---

## 4. Marketing, branding and pricing

Websites and brand work, not application screens. Useful only if COMPASS gets
a public product page; the console and portal should not borrow their hero
photography or large display type.

| Shot | By | Note |
|---|---|---|
| [Cybersecurity Software Website Design - GuardianOS](https://dribbble.com/shots/27485263-Cybersecurity-Software-Website-Design-GuardianOS) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Hero with trust badges (*GDPR Ready*, *SOC 2*) and three proof figures - the pattern for a public privacy-product page |
| [Cybersecurity Pricing Page Design - GuardianOS](https://dribbble.com/shots/27519403-Cybersecurity-Pricing-Page-Design-GuardianOS) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Dark pricing with a segmented *Monthly / Yearly* switch and a slider that updates the estimate live |
| [Paradigm - Tech Consulting Landing Page](https://dribbble.com/shots/26100872-Paradigm-Tech-Consulting-Landing-Page) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Landing page |
| [Paradigm - Tech Mobile-First Landing Page](https://dribbble.com/shots/26583485-Paradigm-Tech-Mobile-First-Landing-Page) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Landing page, phone-first |
| [Paradigm - Mobile-First Low-Code Enablement Service](https://dribbble.com/shots/26492458-Paradigm-Mobile-First-Low-Code-Enablement-Service) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Service page, phone-first |
| [Paradigm - Software Branding UI Design](https://dribbble.com/shots/25937625-Paradigm-Software-Branding-UI-Design) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Brand system |
| [Paradigm - Tech Branding & Logo Design](https://dribbble.com/shots/25820250-Paradigm-Tech-Branding-Logo-Design) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Logo and brand |
| [Paradigm - Abstract Logo Design for Software](https://dribbble.com/shots/26052451-Paradigm-Abstract-Logo-Design-for-Software) | [Phenomenon Studio](https://dribbble.com/phenomenonstudio) | Logo |

---

## 5. From reference to COMPASS

What these references add to the [implementation plan](implementation-plan.md),
in the order it would be built:

| # | Add to COMPASS | From | Plan phase |
|---|---|---|---|
| 1 | **Sparklines in the KPI cards** (30-day trend under each figure) | Promotions UI | 6 Dashboards |
| 2 | **Status as segmented tabs** on lists with few states (Projects, Notices, Breaches: *Open · Closed · All*) | Promotions UI, Risk Assessment | 4 Filters |
| 3 | **Numbered pagination** with "Showing 1-25 of 312" | ERP, Guest List, Risk Assessment | 5 Tables |
| 4 | **Initials avatars** before people's names in tables | ERP, Guest List | 5 Tables |
| 5 | **Export PDF / Excel** buttons on the registers that already export | Guest List | 5 Tables |
| 6 | **Recent activity rail** and **due-soon cards** on the DPO dashboard | Lably | 6 Dashboards |
| 7 | **Request age chart** above the rights-request list | ERP | 6 Dashboards |
| 8 | **Record tabs as pills** with icons on request and breach records | Risk Assessment, Kinetiq | 7 Detail pages |
| 9 | **Readiness checklist with OK states** on the project page | Kinetiq | 7 Detail pages |
| 10 | **Stepper forms with a live summary** for Log an incident and the portal's rights request | ZeBeyond engineering app | 7 Detail pages, 8 Portal |
| 11 | **Quick-look popover** from a list row | RoomSketch | 2 Components (Sheet) |
| 12 | **Dark-mode check** against the developer-tools references | Musemind, Nasir Uddin | 9 Polish |

Rules when borrowing: COMPASS blue rather than the references' greens and
oranges; no stock or hero photography in the apps; every new pattern built
from our tokens and Radix components, and checked with axe.
