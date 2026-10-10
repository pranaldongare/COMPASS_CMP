# Frontend engineering roadmap: React and Next.js, end to end

One ordered reference for building a production frontend with React and
Next.js: the stack, the order to build in, the styling system, the UI
components by name, security, state, performance, accessibility and testing.
It is general guidance, not a description of this repository.

**The order, in one line:**

Plan → Web foundations → React → Next.js → Architecture → Design system →
Components → Layout and navigation → Features → API and state → UI polish →
Security → Accessibility → Performance and SEO → Testing.

---

## Contents

1. [Technology stack](#1-technology-stack)
2. [Build order, phase by phase](#2-build-order-phase-by-phase)
3. [Project structure](#3-project-structure)
4. [Project setup commands](#4-project-setup-commands)
5. [Design system and styling](#5-design-system-and-styling)
6. [UI component catalogue](#6-ui-component-catalogue)
7. [Application modules](#7-application-modules)
8. [API integration and state](#8-api-integration-and-state)
9. [Frontend security](#9-frontend-security)
10. [Accessibility and internationalisation](#10-accessibility-and-internationalisation)
11. [Performance and SEO](#11-performance-and-seo)
12. [Testing and code quality](#12-testing-and-code-quality)
13. [Release checklist](#13-release-checklist)
14. [References](#14-references)

---

## 1. Technology stack

| Layer | Tools | Purpose |
|---|---|---|
| Web foundations | HTML5, CSS3, JavaScript, TypeScript | The base every other layer depends on |
| Framework | React, Next.js App Router | Components, routing, layouts, rendering |
| Language | TypeScript (strict mode) | Type safety and maintainability |
| Styling | Tailwind CSS, CSS variables, CSS Modules where scoped styles help | Consistent, fast styling |
| Component system | shadcn/ui on Radix UI | Accessible, customisable primitives |
| Icons | Lucide React | One consistent icon set |
| Animation | CSS transitions, Motion for React | Transitions and micro-interactions |
| Forms | React Hook Form, Zod | Form state and validation |
| Server data | Fetch API, TanStack Query | Fetching, caching, retries, invalidation |
| Client state | React state and Context; Zustand when genuinely shared | UI state |
| Tables | TanStack Table | Sorting, filtering, pagination |
| Charts | Recharts | Dashboards and analytics |
| Themes | CSS variables, next-themes | Light and dark themes |
| Authentication | Secure server sessions, OAuth 2.0, OpenID Connect | Sign-in and identity |
| Testing | Vitest, React Testing Library, Playwright, axe-core | Unit, component, end-to-end, accessibility |
| Code quality | ESLint, Prettier, TypeScript compiler | Consistency and correctness |
| Performance | Lighthouse, Core Web Vitals | Measuring user experience |
| Security | OWASP guidance, CSP, secure cookies, dependency audits | Protecting users and data |

**Principle:** one styling approach and one component system across the
whole application. Add a library when a requirement calls for it, not on day
one.

---

## 2. Build order, phase by phase

Work through the phases in order. Do not start with animation or page-level
styling before the architecture and design system exist.

### Phase 1: Requirements and planning

- [ ] Define the application's purpose, users, roles and core workflows
- [ ] List every page, route and feature module
- [ ] Draw wireframes and a navigation map
- [ ] Define desktop, tablet and mobile requirements
- [ ] Choose a visual direction: premium SaaS, minimal, or enterprise

### Phase 2: Web foundations

- [ ] Semantic HTML, the DOM and event propagation
- [ ] Native forms and validation
- [ ] The box model, Flexbox and Grid
- [ ] Positioning and stacking contexts
- [ ] Responsive units (`rem`, `em`, `%`, `vw`, `vh`, `clamp()`), media and container queries
- [ ] Cascade, specificity, custom properties and cascade layers
- [ ] JavaScript modules, closures, promises, `async`/`await`, the event loop
- [ ] TypeScript generics, unions, narrowing and utility types
- [ ] Runtime validation versus compile-time types
- [ ] `AbortController` and request cancellation
- [ ] HTTP, headers, status codes, cookies, storage, CORS and the browser security model

### Phase 3: React and Next.js

- [ ] Components, props, state, hooks, context and composition
- [ ] Custom hooks; `memo`, `useMemo`, `useCallback` and profiling
- [ ] App Router: layouts, nested routes, route groups
- [ ] Server Components versus Client Components (server by default; client only for interactivity or browser APIs)
- [ ] SSR, SSG, ISR, streaming and caching
- [ ] `loading.tsx`, `error.tsx`, `global-error.tsx` and `not-found.tsx`
- [ ] Metadata: titles, descriptions, Open Graph

### Phase 4: Project architecture

- [ ] Feature-based folders (see [section 3](#3-project-structure))
- [ ] Clear boundaries between shared components and feature components
- [ ] A typed API client and runtime schemas
- [ ] Environment configuration validated at startup
- [ ] Naming conventions, path aliases, Git workflow and scripts

### Phase 5: Design system

- [ ] Colour palette and semantic tokens
- [ ] Typography scale, spacing, radii, shadows, z-index layers
- [ ] Light and dark theme tokens
- [ ] Focus rings and hover, pressed, disabled and loading states
- [ ] Breakpoints and content widths

Details: [section 5](#5-design-system-and-styling).

### Phase 6: Reusable component library

- [ ] Buttons, inputs, labels, cards, badges, tooltips
- [ ] Dialogs, dropdowns, popovers, drawers and sheets
- [ ] Tabs, accordions, collapsibles, menus, breadcrumbs, pagination
- [ ] Form controls with validation messages
- [ ] Skeletons, empty states, alerts and toasts
- [ ] Keyboard and focus behaviour on every interactive component

Names: [section 6](#6-ui-component-catalogue).

### Phase 7: Application layout and navigation

- [ ] Root layout, header, sidebar and footer
- [ ] Responsive desktop and mobile navigation
- [ ] Breadcrumbs, active menu states and page titles
- [ ] Profile, notification and settings menus
- [ ] Global search and command palette
- [ ] Consistent page widths, spacing and hierarchy

### Phase 8: Features

- [ ] Authentication pages: sign-in, registration, password reset, MFA
- [ ] Dashboard, settings and profile
- [ ] Forms, tables, filters and file uploads
- [ ] Feature modules with their own components, hooks, schemas and services
- [ ] Loading, empty, success and error states on every screen
- [ ] Protected navigation where authentication is required

### Phase 9: API and state

- [ ] Typed requests and responses
- [ ] TanStack Query for server data
- [ ] React state and Context for local state; Zustand only for complex shared client state
- [ ] React Hook Form and Zod for forms
- [ ] Caching, retries, invalidation and cancellation
- [ ] URL search parameters for filters and pagination

Details: [section 8](#8-api-integration-and-state).

### Phase 10: UI polish

- [ ] Visual hierarchy, whitespace and alignment
- [ ] Refined typography, cards, restrained gradients and shadows
- [ ] Hover, focus and pressed states
- [ ] Motion: page, modal and navigation transitions; micro-interactions
- [ ] Skeleton loaders, toasts and useful empty states
- [ ] Every screen reviewed at mobile and desktop sizes

### Phase 11: Security

- [ ] Secure session and token handling
- [ ] Server-enforced authorisation
- [ ] XSS prevention, CSRF protection, CSP and security headers
- [ ] Safe redirects, file handling and dependency auditing
- [ ] No secrets or sensitive data in the client

Details: [section 9](#9-frontend-security).

### Phase 12: Accessibility and internationalisation

- [ ] Keyboard navigation and visible focus
- [ ] Semantic markup and screen-reader labels
- [ ] Contrast and reduced motion
- [ ] Accessible forms, dialogs and notifications
- [ ] Locale-aware dates and numbers; translations when needed

Details: [section 10](#10-accessibility-and-internationalisation).

### Phase 13: Performance and SEO

- [ ] Image and font optimisation
- [ ] Bundle splitting and lazy loading
- [ ] No unnecessary re-renders
- [ ] LCP, INP and CLS measured
- [ ] Metadata, sitemap and canonical URLs for public pages
- [ ] Large tables paginated or virtualised

Details: [section 11](#11-performance-and-seo).

### Phase 14: Testing and quality

- [ ] Unit tests (Vitest)
- [ ] Component tests (React Testing Library)
- [ ] End-to-end tests (Playwright)
- [ ] Accessibility and visual regression checks
- [ ] Lint, type check and production build pass
- [ ] Authentication, permission and failure scenarios tested

Details: [section 12](#12-testing-and-code-quality).

---

## 3. Project structure

A feature-based layout. Add folders as the application grows; do not create
every one on day one.

```text
frontend/
├── public/
│   ├── images/
│   └── icons/
├── src/
│   ├── app/
│   │   ├── (auth)/              # sign-in, register, forgot-password
│   │   ├── (app)/               # signed-in area
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/
│   │   │   └── settings/
│   │   ├── api/                 # only when a Next.js route is genuinely needed
│   │   ├── error.tsx
│   │   ├── global-error.tsx
│   │   ├── loading.tsx
│   │   ├── not-found.tsx
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                  # generic primitives
│   │   ├── layout/              # sidebar, header, navigation
│   │   ├── forms/
│   │   ├── data-display/        # tables, lists, stats
│   │   └── feedback/            # loading, empty, error states
│   ├── features/
│   │   └── <feature>/
│   │       ├── components/
│   │       ├── hooks/
│   │       ├── schemas/
│   │       ├── services/
│   │       └── types/
│   ├── hooks/
│   ├── lib/                     # api-client, query-client, env, auth, utils
│   ├── providers/
│   ├── stores/                  # only if a client store is needed
│   └── types/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── .env.example
├── package.json
└── tsconfig.json
```

**Rule:** a feature's components, hooks, schemas and API services live
together in `features/<feature>/`. `components/ui/` holds only building blocks
reused across the whole application.

---

## 4. Project setup commands

```bash
# Create the application (TypeScript, ESLint, Tailwind, App Router)
npx create-next-app@latest frontend
cd frontend

# Component system
npx shadcn@latest init
npx shadcn@latest add button card input label
npx shadcn@latest add dialog dropdown-menu sheet tabs tooltip
npx shadcn@latest add accordion collapsible table skeleton sonner

# Icons and animation
npm install lucide-react motion

# Forms and validation
npm install react-hook-form zod @hookform/resolvers

# Server data and tables
npm install @tanstack/react-query @tanstack/react-table

# Optional: shared state, charts, themes
npm install zustand recharts next-themes

# Testing
npm install -D vitest @testing-library/react @testing-library/user-event jsdom
npm install -D @playwright/test @axe-core/playwright

npm run dev
```

Check each library's compatibility with your Next.js and Tailwind versions
before installing.

---

## 5. Design system and styling

### 5.1 Tokens

Define these once, as CSS variables, before building pages:

| Token group | Contents |
|---|---|
| Colour | primary, secondary, background, surface, muted, border, text, success, warning, error, info |
| Typography | font families, size scale, line heights, weights, label and code styles |
| Spacing | one scale for padding, margins and gaps; content widths |
| Shape | border radii, borders |
| Elevation | shadows and z-index layers (dropdown, sticky, overlay, modal, toast) |
| Motion | durations and easing curves |
| States | hover, focus, pressed, disabled, loading, selected, error |
| Breakpoints | mobile, tablet, desktop, wide |

Example:

```css
/* app/globals.css */
@import "tailwindcss";

:root {
  --background: #ffffff;
  --foreground: #171717;
  --surface: #ffffff;
  --muted: #f4f4f5;
  --border: #e4e4e7;
  --primary: #2f6fb5;
  --destructive: #dc2626;
  --radius: 0.75rem;
}

.dark {
  --background: #09090b;
  --foreground: #fafafa;
  --surface: #18181b;
  --muted: #27272a;
  --border: #3f3f46;
  --primary: #7fb3e8;
  --destructive: #f87171;
}
```

If you use shadcn/ui, align these with its generated theme rather than
keeping two competing colour systems.

### 5.2 Layout engineering

- Responsive grids with CSS Grid; one-dimensional layouts with Flexbox
- Fluid typography with `clamp()`
- Container queries for components that live in panels of varying width
- Sticky headers and sidebars
- Readable content widths and generous whitespace
- Mobile-first breakpoints

### 5.3 Visual style

- Minimal, editorial, premium SaaS or enterprise: pick one and keep to it
- Soft shadows and layered surfaces; restrained gradients
- Consistent icons and illustrations
- Glassmorphism only where contrast stays readable
- Light and dark themes from the same tokens

### 5.4 Motion

- CSS transitions and keyframes for simple states
- Motion for React for page, modal and list transitions
- Skeletons and loading indicators instead of spinners where layout is known
- Respect `prefers-reduced-motion`
- Avoid animation that delays the user or causes layout jank

### 5.5 Styling technologies by priority

| Technology | Priority | Best use |
|---|---|---|
| CSS fundamentals | Critical | The base of everything |
| CSS variables | Critical | Tokens and themes |
| Tailwind CSS | Critical | Utility styling |
| shadcn/ui | Critical | Component foundation |
| Radix UI | High | Accessible interaction primitives |
| CSS Modules | High | Scoped component styles |
| Motion for React | High | Interactive animation |
| Sass/SCSS | Medium | Existing Sass codebases |
| Stylelint | Medium | CSS quality checks |

### 5.6 Rules for a premium look

- **Layout and spacing:** one spacing scale, clear hierarchy, aligned edges, room to breathe.
- **Typography and colour:** one primary font, a clear size and weight hierarchy, a restrained palette, strong contrast, consistent semantic colours.
- **Components and motion:** consistent radii, subtle shadows, a clear button hierarchy, smooth but quick transitions.
- **Responsive behaviour:** tables, dialogs, sidebars, charts and forms stay usable on touch screens.

---

## 6. UI component catalogue

The common names used in modern admin panels and SaaS applications, grouped
by purpose.

### 6.1 Sidebar navigation

`Sidebar`, `SidebarHeader`, `SidebarContent`, `SidebarFooter`,
`SidebarGroup`, `SidebarGroupLabel`, `SidebarMenu`, `SidebarMenuItem`,
`SidebarMenuButton`, `SidebarMenuBadge`, `SidebarSubMenu`,
`SidebarTrigger`, `SidebarRail`, `CollapsibleSidebar`, `MiniSidebar`
(icons only), `ResizableSidebar`, `MobileSidebar` (drawer).

### 6.2 Navbar and top navigation

`Navbar` / `TopNavbar`, `Header`, `HeaderActions`, `MainNavigation`,
`NavigationMenu`, `NavigationMenuItem`, `NavLink`, `NavDropdown`,
`MegaMenu`, `Breadcrumb`, `BreadcrumbItem`, `CommandMenu` /
`CommandPalette`, `GlobalSearch`, `UserMenu`, `NotificationMenu`,
`ThemeToggle`.

### 6.3 Page layout

`AppShell`, `DashboardLayout`, `AdminLayout`, `AuthLayout`, `MainLayout`,
`PageLayout`, `PageHeader`, `PageContent`, `PageFooter`, `Container`,
`ContentContainer`, `Section`, `StickyHeader`, `StickyFooter`,
`SplitLayout`.

### 6.4 Grid system and responsive layout

| Component | Purpose |
|---|---|
| `Container` | Centres and constrains content |
| `Grid`, `GridItem` | Two-dimensional layouts |
| `Row`, `Column` | Horizontal grouping, vertical division |
| `Flex` | One-dimensional layout |
| `Stack` | Even vertical or horizontal spacing |
| `Inline` | Content in a row that wraps |
| `ResponsiveGrid`, `AutoGrid` | Column count follows screen width |
| `CardGrid` | Cards in a grid |
| `DashboardGrid` | KPI and analytics layouts |
| `BentoGrid` | Mixed-size modern dashboard tiles |
| `MasonryGrid` | Uneven-height tiles |
| `SplitGrid` | Unequal two-column layouts |
| `AspectRatio` | Fixed-ratio media |
| `Divider` / `Separator` | Visual separation |
| `Spacer` | Explicit space |

### 6.5 Tabs

`Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`, `ScrollableTabs`,
`IconTabs`, `VerticalTabs`, `NestedTabs`, `TabBadge`, `TabActions`.

### 6.6 Accordion

`Accordion`, `AccordionItem`, `AccordionTrigger`, `AccordionContent`,
`SingleExpandAccordion`, `MultiExpandAccordion`, `FAQAccordion`.

### 6.7 Collapse and expand

`Collapsible`, `CollapsibleTrigger`, `CollapsibleContent`,
`Disclosure`, `ExpandButton`, `CollapseButton`, `ExpandablePanel`,
`ExpandableCard`, `ShowMore`, `TreeView`, `NestedTreeView`.

### 6.8 Panels and split views

`Panel`, `PanelHeader`, `PanelContent`, `PanelFooter`, `PanelGroup`,
`ResizablePanel`, `ResizableHandle`, `SplitPane`, `SidePanel`,
`InspectorPanel`, `Drawer`, `Sheet`.

### 6.9 Tables and data grids

**Basic:** `Table`, `TableHeader`, `TableBody`, `TableFooter`, `TableRow`,
`TableHead`, `TableCell`, `TableCaption`.

**Advanced:** `DataTable`, `DataGrid`, `SortableTable`, `FilterableTable`,
`PaginatedTable`, `SelectableTable`, `ExpandableTable`, `GroupedTable`,
`NestedTable`, `EditableTable`, `ServerSideTable`, `VirtualizedTable`,
`InfiniteScrollTable`, `PinnedColumnTable`, `ResizableColumnTable`,
`DraggableColumnTable`.

**Controls:** `TableToolbar`, `TableSearch`, `GlobalFilter`,
`ColumnFilter`, `ColumnVisibilityMenu`, `SortButton`, `Pagination`,
`PageSizeSelector`, `BulkActions`, `RowActions`, `ExportButton`,
`EmptyTableState`, `TableSkeleton`.

### 6.10 Forms and inputs

`Form`, `FormField`, `FormItem`, `FormLabel`, `FormControl`,
`FormDescription`, `FormMessage`, `Input`, `Textarea`, `Select`,
`Combobox`, `MultiSelect`, `Checkbox`, `CheckboxGroup`, `RadioGroup`,
`Switch`, `Slider`, `DatePicker`, `DateRangePicker`, `TimePicker`,
`FileUpload`, `Dropzone`, `OTPInput`, `PasswordInput`, `SearchInput`,
`TagInput`, `Stepper` / `MultiStepForm`.

### 6.11 Buttons and actions

`Button` (primary, secondary, outline, ghost, destructive, link),
`IconButton`, `ButtonGroup`, `SplitButton`, `ToggleButton`,
`ToggleGroup`, `CopyButton`, `LoadingButton`.

### 6.12 Overlays

`Dialog` / `Modal`, `AlertDialog` / `ConfirmDialog`, `Drawer`, `Sheet`,
`Popover`, `HoverCard`, `Tooltip`, `DropdownMenu`, `ContextMenu`,
`Menubar`.

### 6.13 Feedback and status

`Alert`, `Banner`, `Toast` / `Sonner`, `Progress`, `CircularProgress`,
`Spinner`, `Skeleton`, `EmptyState`, `ErrorState`, `SuccessState`,
`StatusBadge`, `Callout`.

### 6.14 Data display

`Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`,
`CardFooter`, `StatCard` / `KPICard`, `Badge`, `Avatar`, `AvatarGroup`,
`List`, `DescriptionList`, `Timeline`, `ActivityFeed`, `Chart`,
`Sparkline`, `Kbd`, `CodeBlock`, `Markdown`.

### 6.15 Navigation helpers

`Pagination`, `Steps`, `Anchor` / `TableOfContents`, `BackLink`,
`SkipToContent`.

---

## 7. Application modules

Enable only what the application needs.

| Module | Contents |
|---|---|
| Design system | Colours, typography, spacing, shadows, tokens |
| Application shell | Header, sidebar, footer, responsive navigation |
| Authentication | Sign-in, registration, password reset, MFA, session states |
| Dashboard | KPI cards, charts, activity feed, summary panels |
| Forms | Validation, field errors, multi-step flows, file uploads |
| Data management | Tables, sorting, search, filtering, pagination, bulk actions |
| Search | Global search, autocomplete, filters, command palette, shortcuts |
| Notifications | Toasts, alerts, notification centre, unread state, preferences |
| User account | Profile, avatar, preferences, settings |
| Overlays | Dialogs, drawers, popovers, confirmation prompts |
| Files | Upload progress, previews, downloads |
| Rich content | Markdown, code blocks, syntax highlighting |
| Themes | Light and dark mode, remembered preference |
| Empty and error states | Skeletons, empty screens, retry actions, error pages |
| Internationalisation | Translations, locale-aware dates and numbers, RTL if needed |
| Accessibility | Keyboard support, focus management, screen-reader labels |

---

## 8. API integration and state

### 8.1 Request flow

1. The user acts in a component.
2. A feature hook calls its API service.
3. The typed API client sends the request.
4. The backend authenticates the caller and checks authorisation.
5. The backend runs the operation.
6. The frontend shows the data, progress or a meaningful error.
7. TanStack Query refreshes the cached data the operation changed.

### 8.2 API client essentials

- [ ] One typed client with the base URL from configuration
- [ ] Credentials and CSRF header handled in one place
- [ ] Timeouts, retry policy and cancellation
- [ ] A standard error shape, with request IDs for support
- [ ] Session expiry and unauthorised responses handled centrally

### 8.3 Which state goes where

| Kind of state | Tool |
|---|---|
| Component state | `useState`, `useReducer` |
| Small shared state (theme, auth context) | React Context |
| Complex shared client state | Zustand |
| Server data | TanStack Query |
| Form state | React Hook Form |
| Validation | Zod |
| Shareable filters, search, pagination | URL search parameters |
| Server-rendered data | Server Components |
| Large or offline browser data | IndexedDB |
| Real-time updates | WebSockets or Server-Sent Events |

Keep server state, UI state, form state and URL state apart. Do not put
everything into one global store.

---

## 9. Frontend security

The backend is the security boundary. The frontend's job is to avoid
weakening it.

### 9.1 Authentication and sessions

- [ ] Sessions in `HttpOnly`, `Secure` cookies with an appropriate `SameSite`
- [ ] No session tokens or secrets in `localStorage`
- [ ] Session expiry, sign-out, renewal and revocation
- [ ] OAuth 2.0 / OpenID Connect through a trusted provider, or correct server sessions
- [ ] MFA for privileged roles
- [ ] No passwords or long-lived secrets in frontend code

### 9.2 Authorisation

- [ ] Role-based access control enforced on the server for every protected operation
- [ ] Resource ownership and tenant checks on the server
- [ ] Deny by default when a permission is unknown
- [ ] Hidden buttons and route guards are convenience, never the boundary

### 9.3 Browser vulnerabilities

- [ ] XSS: escape output; sanitise any untrusted HTML; avoid `dangerouslySetInnerHTML`
- [ ] CSRF protection matching the session design
- [ ] Clickjacking: `frame-ancestors` / `X-Frame-Options`
- [ ] Open redirects: only same-origin paths in `next=` parameters
- [ ] Forms posted with `method="post"`, so an unhydrated submit never puts fields in the URL

### 9.4 Network and headers

- [ ] HTTPS everywhere; HSTS
- [ ] Content Security Policy, ideally with a per-request nonce
- [ ] `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`
- [ ] CORS configured on the server, narrowly
- [ ] Rate limiting and abuse protection on the backend

### 9.5 Files, privacy and data

- [ ] File type and size validated on client and server
- [ ] File names and contents treated as untrusted
- [ ] No personal data in URLs, logs or analytics
- [ ] No secrets in error messages or public source maps
- [ ] Downloads checked for permission on the server
- [ ] Only `NEXT_PUBLIC_` values that are safe to publish

### 9.6 Supply chain

- [ ] Lock files committed
- [ ] `npm audit` or equivalent run regularly
- [ ] Few, well-maintained dependencies

---

## 10. Accessibility and internationalisation

Target **WCAG 2.2 Level AA**.

- [ ] Semantic HTML and a meaningful heading order
- [ ] Every feature usable by keyboard
- [ ] Visible focus indicators
- [ ] Labels on every input; errors announced and linked to their fields
- [ ] Accessible names on icon-only buttons
- [ ] Sufficient colour contrast; status never shown by colour alone
- [ ] Focus trapped in dialogs and returned on close
- [ ] Live regions for toasts and async results
- [ ] `prefers-reduced-motion` respected
- [ ] Touch targets large enough on mobile
- [ ] Locale-aware dates, numbers and currencies; translations and RTL when required
- [ ] Automated checks (axe) plus manual keyboard and screen-reader testing

---

## 11. Performance and SEO

### 11.1 Performance

- [ ] Server Components by default; Client Components only where needed
- [ ] `next/image` and `next/font`
- [ ] Code splitting and lazy loading of heavy features
- [ ] No unnecessary re-renders or expensive work on every render
- [ ] Pagination, and virtualisation for very long lists
- [ ] Third-party scripts kept to a minimum and loaded late
- [ ] Stable dimensions to prevent layout shift
- [ ] Appropriate caching and revalidation
- [ ] Bundle analysis

**Core Web Vitals targets (75th percentile):** LCP ≤ 2.5 s, INP ≤ 200 ms,
CLS ≤ 0.1. Measure with Lighthouse.

### 11.2 SEO (public pages)

- [ ] Unique titles and descriptions
- [ ] Open Graph and share previews
- [ ] Canonical URLs, sitemap and robots directives
- [ ] Structured data where relevant
- [ ] Friendly 404 and error pages

Authenticated dashboards need accessibility, usability and speed more than
search indexing.

---

## 12. Testing and code quality

| Level | Tools |
|---|---|
| Unit | Vitest |
| Component | React Testing Library |
| API mocking | MSW |
| End to end | Playwright |
| Accessibility | axe-core with Playwright |
| Visual regression | Playwright screenshots |
| Types | TypeScript compiler |
| Lint and format | ESLint, Prettier |
| Dependencies | `npm audit` |
| Performance | Lighthouse |

Test real journeys: sign-in, form submission, permissions, data loading,
session expiry, failure recovery and mobile navigation, not only that
components render.

---

## 13. Release checklist

- [ ] Every required page and route works
- [ ] Shared components use the design tokens
- [ ] Mobile, tablet and desktop layouts verified
- [ ] Forms validate and explain their errors
- [ ] Loading, empty, success and failure states handled
- [ ] Keyboard navigation and visible focus work
- [ ] Light and dark themes work, if offered
- [ ] Images, fonts and rendering optimised
- [ ] Authentication and authorisation enforced on the server
- [ ] Security headers and CSP in place
- [ ] Tests, lint, type check and production build pass

---

## 14. References

- Next.js App Router: <https://nextjs.org/docs/app>
- React: <https://react.dev>
- Tailwind CSS: <https://tailwindcss.com/docs>
- shadcn/ui: <https://ui.shadcn.com/docs>
- Radix UI: <https://www.radix-ui.com/primitives>
- TanStack Query: <https://tanstack.com/query/latest>
- Playwright: <https://playwright.dev>
- OWASP Cheat Sheet Series: <https://cheatsheetseries.owasp.org>
- OWASP ASVS: <https://owasp.org/www-project-application-security-verification-standard/>
- WCAG 2.2: <https://www.w3.org/TR/WCAG22/>
- Core Web Vitals: <https://web.dev/articles/vitals>
