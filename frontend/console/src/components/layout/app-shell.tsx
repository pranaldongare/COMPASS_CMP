/**
 * The authenticated shell: sidebar, header, content region.
 *
 * Navigation is rendered from `me.nav`, which the server computes from the
 * permission matrix. The frontend does not decide who sees what - it would be a
 * second copy of the rules, and a second copy drifts.
 *
 * The sidebar groups those destinations into sections. The grouping is purely
 * presentational: a section renders only when the server has granted at least
 * one item inside it, so a role with three destinations gets three links and no
 * empty headings.
 */
"use client";

import {
  Bell,
  ChevronDown,
  House,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";

import {
  CommandPalette,
  rememberVisit,
  useCommandPaletteShortcut,
} from "@/components/layout/command-palette";
import {
  destinationOf,
  labelFor,
  locate,
  sectionsFor,
  sidebarFor,
  type NavSection,
} from "@/components/layout/nav";
import { PillTrail, type Crumb } from "@/components/layout/pill-trail";
import { useDrawer } from "@/components/layout/use-drawer";
import { UserMenu } from "@/components/layout/user-menu";
import { useCollapsed } from "@/components/ui/collapsible";
import { BrandMark } from "@/components/ui/graphics";
import { Tooltip } from "@/components/ui/overlay";
import { Button } from "@/components/ui/primitives";
import { config } from "@/lib/config";
import { cn } from "@/lib/format";
import { useMyTickets, useRequestsAttention } from "@/features/rights/queries";
import { useAuth } from "@/providers";
// Straight from the module: page tests stand in for "@/providers" and the
// header must render without a session there.
import { useOptionalAuth } from "@/providers/auth-provider";

/* The desktop sidebar can fold to a rail of icons. The choice is this
   browser's convenience, so it lives in localStorage - which can be missing or
   throw, and then the choice lasts only until the page is reloaded. */
const SIDEBAR_KEY = "cmp.console.sidebar";
const sidebarListeners = new Set<() => void>();
let sidebarFallback = false;

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === "collapsed";
  } catch {
    return sidebarFallback;
  }
}

function writeCollapsed(collapsed: boolean): void {
  sidebarFallback = collapsed;
  try {
    if (collapsed) localStorage.setItem(SIDEBAR_KEY, "collapsed");
    else localStorage.removeItem(SIDEBAR_KEY);
  } catch {
    // Kept in memory instead.
  }
  sidebarListeners.forEach((notify) => notify());
}

function useSidebarCollapsed(): [boolean, (collapsed: boolean) => void] {
  const collapsed = React.useSyncExternalStore(
    (notify) => {
      sidebarListeners.add(notify);
      return () => sidebarListeners.delete(notify);
    },
    readCollapsed,
    // The server renders the full sidebar; a folded one appears after hydration.
    () => false,
  );
  return [collapsed, writeCollapsed];
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me } = useAuth();
  const pathname = usePathname();
  // The drawer is open for one route. Navigating anywhere closes it, which is
  // derived here rather than done in an effect: an effect would render the
  // drawer over the new page for one frame before closing it.
  const [openedAt, setOpenedAt] = React.useState<string | null>(null);
  const mobileOpen = openedAt === pathname;
  const setMobileOpen = React.useCallback(
    (open: boolean) => setOpenedAt(open ? pathname : null),
    [pathname],
  );
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const togglePalette = React.useCallback(() => setPaletteOpen((open) => !open), []);
  useCommandPaletteShortcut(togglePalette);
  const [collapsed, setCollapsed] = useSidebarCollapsed();

  // The server says which sections this role has; nothing renders that it
  // did not grant.
  const sections = sectionsFor(me);
  const here = locate(sections, pathname);
  const hereHref = here?.item.href;

  // The palette's "Recent" group: the destinations visited, not every detail
  // page under them.
  React.useEffect(() => {
    if (hereHref) rememberVisit(hereHref);
  }, [hereHref]);

  return (
    // Deliberately no background on this element: `body` already paints the
    // page colour, and a second opaque layer here would sit on top of the wash
    // below and hide it.
    <div className="relative min-h-dvh">
      {/* No top bar on a desk (2026-10-10): the sidebar carries the logo,
          the search, notifications and the settings menu. A phone keeps a
          slim bar, since its sidebar is a closed drawer. */}
      <MobileBar onMenuClick={() => setMobileOpen(!mobileOpen)} mobileOpen={mobileOpen} />

      <div className="flex w-full">
        <Sidebar
          sections={sidebarFor(me)}
          pathname={pathname}
          mobileOpen={mobileOpen}
          collapsed={collapsed}
          onToggleCollapsed={() => setCollapsed(!collapsed)}
          onClose={() => setMobileOpen(false)}
        />

        {/* Inert under the open drawer: not reachable by Tab, not read out. */}
        {/* The page straight on the grey (2026-10-10): no panel, border or
            rounding round it; its cards and tables are white. */}
        <main id="main" inert={mobileOpen} className="min-w-0 flex-1 bg-[var(--page-bg)]">
          <div className="min-h-[calc(100dvh-4rem)] px-4 py-6 sm:px-6 lg:min-h-dvh lg:px-8">
            {children}
          </div>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}

/** The COMPASS lockup: the shield and the two-tone name. */
function Lockup({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      href="/dashboard"
      aria-label={config.productName}
      className="group flex shrink-0 items-center gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]"
    >
      <BrandMark className="size-7 shrink-0 text-accent-text" />
      <span className={cn("block text-lg leading-none font-bold tracking-tight", compact && "lg:hidden")}>
        <span className="text-accent-text">{config.productName.slice(0, 3)}</span>
        <span className="text-text-muted">{config.productName.slice(3)}</span>
      </span>
    </Link>
  );
}

/** A phone's bar: the drawer's button, the logo and the account circle. Gone from `lg` up, where the sidebar carries all of it. */
function MobileBar({
  onMenuClick,
  mobileOpen,
}: {
  onMenuClick: () => void;
  mobileOpen: boolean;
}) {
  return (
    <header className="frame-light no-print sticky top-0 z-30 border-b border-border bg-surface lg:hidden">
      <div className="flex h-16 w-full items-center gap-3 px-4 sm:px-6">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          aria-expanded={mobileOpen}
          aria-controls="sidebar-nav"
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
        >
          {mobileOpen ? <X /> : <Menu />}
        </Button>
        <Lockup />
        <div className="flex-1" />
        <UserMenu />
      </div>
    </header>
  );
}

function Sidebar({
  sections,
  pathname,
  mobileOpen,
  collapsed,
  onToggleCollapsed,
  onClose,
}: {
  sections: NavSection[];
  pathname: string;
  mobileOpen: boolean;
  /** Folded to icons. Desktop only: the phone drawer always shows words. */
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onClose: () => void;
}) {
  const { me } = useAuth();
  // Folding applies from the desktop breakpoint up; these are the classes that
  // do it, so the drawer on a phone is untouched.
  const folded = collapsed && !mobileOpen;
  const drawer = useDrawer<HTMLElement>(mobileOpen, onClose);
  return (
    <>
      {/* Scrim. Clicking it closes the drawer; it is hidden from assistive tech
          because the drawer's own close button and Escape already do the job. */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 backdrop-blur-[2px] lg:hidden"
          aria-hidden="true"
          onClick={onClose}
        />
      )}

      <nav
        ref={drawer}
        id="sidebar-nav"
        aria-label="Main"
        data-collapsed={folded || undefined}
        className={cn(
          // Line (2026-10-10): white down the left, white in both themes.
          "frame-light sidebar-glow no-print z-20 flex w-64 shrink-0 flex-col border-r border-border bg-[var(--sidebar-bg)] text-[var(--sidebar-text)]",
          "lg:sticky lg:top-0 lg:h-dvh lg:transition-[width] lg:duration-200",
          folded && "lg:w-[4.5rem]",
          mobileOpen
            ? "fixed top-16 bottom-0 left-0 flex overflow-y-auto shadow-[var(--shadow-pop)]"
            : "hidden lg:flex",
        )}
      >
        {mobileOpen && (
          <div className="flex justify-end border-b border-[var(--sidebar-border)] px-3 py-2 lg:hidden">
            <Button
              variant="ghost"
              className="text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text-strong)]"
              onClick={onClose}
            >
              Close menu
            </Button>
          </div>
        )}
        {/* The head (2026-10-10): the logo; the phone bar's job below lg.
            Jump to page is the keyboard's (Ctrl/Cmd K), not a box here. */}
        <div
          className={cn(
            "hidden h-16 shrink-0 items-center lg:flex",
            folded ? "justify-center" : "px-5",
          )}
        >
          <Lockup compact={folded} />
        </div>
        <div
          className={cn(
            "sidebar-scroll flex-1 overflow-x-hidden overflow-y-auto py-4",
            folded ? "lg:px-3" : "px-3",
          )}
        >
          {sections.map((section, i) => (
            <NavGroup
              key={section.title}
              title={section.title}
              folded={folded}
              first={i === 0}
              current={section.items.some(
                (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
              )}
            >
              {section.items.map((item) => {
                const active =
                  pathname === item.href || pathname.startsWith(`${item.href}/`);
                const Icon = item.icon;
                const label = labelFor(item, me?.role);
                return (
                  <li key={`${section.title}:${item.href}`}>
                    {/* Folded, the word is visually hidden but still the
                        link's name; the chip beside the icon is for sighted
                        users, on hover and on keyboard focus. */}
                    <Tooltip content={folded ? label : null} side="right">
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "group relative flex items-center gap-3 rounded-xl py-1.5 pr-2 pl-1.5 text-sm",
                        "transition-[background-color,color,box-shadow] duration-150",
                        "outline-none focus-visible:ring-2 focus-visible:ring-[var(--sidebar-badge)]",
                        folded && "lg:size-11 lg:justify-center lg:p-0",
                        // Active: a blue gradient pill (.nav-current), white text.
                        active
                          ? "nav-current font-semibold"
                          : "hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text-strong)]",
                      )}
                    >
                      <span aria-hidden="true" className={`nav-tile nav-tint-${i % 4}`}>
                        <Icon className="size-4" />
                      </span>
                      <span className={cn("truncate", folded && "lg:sr-only")}>
                        {label}
                      </span>
                      {item.key === "tickets" && <TicketsBadge folded={folded} />}
                      {item.key === "requests" && <RequestsBadge folded={folded} />}
                    </Link>
                    </Tooltip>
                  </li>
                );
              })}
            </NavGroup>
          ))}
        </div>

        <div
          className={cn(
            // Solid: the footer is a block of its own, never a veil over the
            // last links.
            "shrink-0 space-y-0.5 border-t border-[var(--sidebar-border)]",
            folded ? "lg:p-3" : "p-3",
          )}
        >
          {me?.nav.includes("notifications") && (
            <Tooltip content={folded ? "Notifications" : null} side="right">
              <Link
                href="/notifications"
                aria-current={pathname === "/notifications" ? "page" : undefined}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl py-1.5 pr-2 pl-1.5 text-sm text-[var(--sidebar-text)]",
                  "outline-none focus-visible:ring-2 focus-visible:ring-[var(--sidebar-badge)]",
                  pathname === "/notifications"
                    ? "nav-current font-semibold"
                    : "hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text-strong)]",
                  folded && "lg:size-11 lg:justify-center lg:px-0",
                )}
              >
                <span aria-hidden="true" className="nav-tile nav-tint-0">
                  <Bell className="size-4" />
                </span>
                <span className={cn(folded && "lg:sr-only")}>Notifications</span>
              </Link>
            </Tooltip>
          )}
          <Tooltip content={folded ? "Expand sidebar" : null} side="right">
          <Button
            variant="ghost"
            className={cn(
              "hidden w-full justify-start rounded-lg px-3 text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text-strong)] lg:flex",
              folded && "lg:size-11 lg:justify-center lg:px-0",
            )}
            onClick={onToggleCollapsed}
            aria-expanded={!folded}
            aria-controls="sidebar-nav"
          >
            {folded ? (
              <PanelLeftOpen className="size-4" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="size-4" aria-hidden="true" />
            )}
            <span className={cn(folded && "lg:sr-only")}>
              {folded ? "Expand sidebar" : "Collapse sidebar"}
            </span>
          </Button>
          </Tooltip>
          {/* The settings menu at the very end: profile, manual, theme and
              signing out (2026-10-10). */}
          <UserMenu placement="sidebar" folded={folded} />
        </div>
      </nav>
    </>
  );
}

/**
 * One group of the sidebar - Governance, Consent … - whose heading folds its
 * links away. The choice is remembered per group in this browser. The group
 * holding the page you are on stays open whatever was chosen, so the current
 * page is never hidden, and on the folded icon rail every group shows.
 */
function NavGroup({
  title,
  folded,
  first,
  current,
  children,
}: {
  title: string;
  folded: boolean;
  first: boolean;
  current: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useCollapsed(`nav.${title}`, true);
  const listId = React.useId();
  const shown = open || current || folded;
  return (
    <div className={cn("last:mb-0", shown ? "mb-5" : "mb-1.5")}>
      <button
        type="button"
        aria-expanded={shown}
        aria-controls={listId}
        onClick={() => setOpen(!open)}
        title={current ? "Holds the page you are on" : undefined}
        className={cn(
          "group mb-1.5 flex w-full items-center justify-between rounded-md px-3 py-0.5 text-2xs font-semibold tracking-wider text-[var(--sidebar-label)] uppercase",
          "transition-colors outline-none hover:text-[var(--sidebar-text)] focus-visible:ring-2 focus-visible:ring-[var(--sidebar-badge)]",
          folded && "lg:sr-only",
        )}
      >
        {title}
        <ChevronDown
          aria-hidden="true"
          className={cn(
            "size-3.5 opacity-0 transition-[transform,opacity] group-hover:opacity-100 group-focus-visible:opacity-100",
            !shown && "-rotate-90 opacity-100",
          )}
        />
      </button>
      {/* Folded, a hairline stands in for the heading so the groups
          still read as groups. */}
      {folded && !first && (
        <div aria-hidden="true" className="mx-2 mb-2 hidden h-px bg-[var(--sidebar-border)] lg:block" />
      )}
      <ul id={listId} hidden={!shown} className="space-y-0.5">
        {children}
      </ul>
    </div>
  );
}

/** The steps to this page from the dashboard: the menu destination it sits
 *  under, then the page itself when it is a record under that destination.
 *  None on the dashboard. */
function trailFor(pathname: string, title: string, role: string | undefined): Crumb[] {
  if (pathname === "/dashboard" || pathname === "/") return [];
  const home: Crumb = { label: "Dashboard", href: "/dashboard", icon: House };
  const dest = destinationOf(pathname);
  if (!dest) return [home, { label: title }];
  const label = labelFor(dest, role);
  if (dest.href === pathname) return [home, { label, icon: dest.icon }];
  return [home, { label, href: dest.href, icon: dest.icon }, { label: title }];
}

/** Page heading with optional description and actions. Used on every page so
 *  the vertical rhythm is identical throughout. */
export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
  eyebrow,
  hero = false,
}: {
  title: string;
  /** Shown only on a record's own page (2026-10-10), where it is the
   *  record's data - an incident's title, a request's kind. A destination's
   *  explanatory sentence is not shown; it is in the help. */
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  /** A short kicker above the title - the section this page belongs to. */
  eyebrow?: string;
  /** Not shown (2026-10-10): the icon tile beside the title was removed. */
  icon?: React.ComponentType<{ className?: string }> | null;
  /** The page's opening banner (2026-10-10): the header on a white card with
   *  a field of blue dots - the dashboard's greeting. */
  hero?: boolean;
}) {
  const pathname = usePathname() ?? "";
  const role = useOptionalAuth()?.me?.role;
  const crumbs = trailFor(pathname, title, role);
  // The trail names the page (2026-10-10): where there is one, the title is
  // for screen readers only and the page's actions share the trail's row.
  if (!hero && crumbs.length > 0) {
    return (
      <div className="mb-5">
        <h1 className="sr-only">{title}</h1>
        <div className="flex flex-wrap items-center gap-3">
          <PillTrail crumbs={crumbs} extra={breadcrumb} className="mb-0 max-w-full min-w-0 flex-auto" />
          {/* The kicker still says what kind of record this is - an incident
              being validated, a personal data breach - beside the trail. */}
          {eyebrow && (
            <p className="order-first w-full text-2xs font-semibold tracking-wider text-accent-text uppercase">
              {eyebrow}
            </p>
          )}
          {/* A record's own line - its title, its kind - under the trail. */}
          {description && crumbs.length > 2 && (
            <p className="order-last w-full text-sm text-text-muted">{description}</p>
          )}
          {actions && (
            // When they do not fit beside the trail, the actions take the next
            // line, at the right, rather than squeezing the trail onto two.
            <div
              className="ml-auto flex max-w-full min-w-0 flex-wrap items-center justify-end gap-2"
              data-testid="page-actions"
            >
              {actions}
            </div>
          )}
        </div>
      </div>
    );
  }
  return (
    <div
      className={cn(
        "mb-5",
        hero && "hero-line mb-6 overflow-hidden rounded-2xl border border-border px-6 py-6 shadow-[var(--shadow-card)] sm:px-7",
      )}
    >
      {/* The pill trail (2026-10-10); a page's own back link at its end. */}
      {hero ? (
        breadcrumb && <div className="mb-2 text-sm text-text-muted">{breadcrumb}</div>
      ) : (
        <PillTrail crumbs={crumbs} extra={breadcrumb} />
      )}
      {/* On a desk the actions keep their place at the right (2026-10-10):
          the heading gives way - its line clamps - rather than pushing them
          down under it. */}
      <div className="flex flex-wrap items-start justify-between gap-3 lg:flex-nowrap">
        <div className="flex min-w-0 items-start gap-4 lg:flex-1">
          <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1 text-2xs font-semibold tracking-wider text-accent-text uppercase">
              {eyebrow}
            </p>
          )}
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          </div>
        </div>
        {actions && (
          <div
            className="flex max-w-full min-w-0 flex-wrap items-center gap-2 lg:shrink-0 lg:flex-nowrap"
            data-testid="page-actions"
          >
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * How many of this person's open tickets carry something they have not read
 * - a new ticket, a message from the Privacy Office, a ticket sent back.
 * The one conversation staff are in should be visible from every page.
 */
function TicketsBadge({ folded }: { folded: boolean }) {
  const tickets = useMyTickets();
  const count = (tickets.data ?? []).filter(
    (t) =>
      (t.ticket_status === "issued" || t.ticket_status === "escalated") &&
      t.unread_for_holder > 0,
  ).length;
  return (
    <NavCount
      count={count}
      folded={folded}
      label={`${count} ticket${count === 1 ? "" : "s"} with unread messages`}
    />
  );
}

/** The office's side of the same bell: open tickets a team has written on
 * that nobody in the office has read. Cleared by opening the thread. */
function RequestsBadge({ folded }: { folded: boolean }) {
  const attention = useRequestsAttention();
  const count = attention.data?.threads_unread ?? 0;
  return (
    <NavCount
      count={count}
      folded={folded}
      label={`${count} ticket thread${count === 1 ? "" : "s"} unread`}
    />
  );
}

function NavCount({
  count,
  label,
  folded,
}: {
  count: number;
  label: string;
  folded: boolean;
}) {
  if (!count) return null;
  return (
    <span
      className={cn(
        "ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-[var(--sidebar-badge)] px-1.5 text-2xs font-semibold text-[var(--sidebar-badge-text)]",
        // On the blue current-page pill the count turns white with blue text.
        "group-aria-[current=page]:bg-white group-aria-[current=page]:text-[#1f5c9e]",
        // Folded, the count sits on the icon's corner, like a badge on an app.
        folded &&
          "lg:absolute lg:top-0.5 lg:right-1 lg:ml-0 lg:min-w-4 lg:px-1 lg:text-[0.625rem] lg:leading-4",
      )}
      aria-label={label}
    >
      {count}
    </span>
  );
}
