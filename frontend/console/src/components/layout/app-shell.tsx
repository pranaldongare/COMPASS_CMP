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
  ChevronRight,
  CircleHelp,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
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
import { iconForPage, labelFor, locate, sectionsFor, sidebarFor, type NavSection } from "@/components/layout/nav";
import { HelpLink } from "@/components/layout/help-link";
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

/** ⌘ on Apple keyboards, Ctrl elsewhere. The server does not know which. */
function useIsApple(): boolean {
  return React.useSyncExternalStore(
    () => () => {},
    () => /Mac|iPhone|iPad/.test(navigator.userAgent),
    () => false,
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, signOut } = useAuth();
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
      {/* One soft wash behind the whole shell. Fixed rather than scrolling, so
          it behaves like light in the room instead of a background image. */}
      <div aria-hidden="true" className="aurora pointer-events-none fixed inset-0 -z-10" />

      <Header
        onMenuClick={() => setMobileOpen(!mobileOpen)}
        mobileOpen={mobileOpen}
        onSearch={() => setPaletteOpen(true)}
        here={here}
        pathname={pathname}
      />

      <div className="flex w-full">
        <Sidebar
          sections={sidebarFor(me)}
          pathname={pathname}
          mobileOpen={mobileOpen}
          collapsed={collapsed}
          onToggleCollapsed={() => setCollapsed(!collapsed)}
          onClose={() => setMobileOpen(false)}
          onSignOut={signOut}
        />

        {/* Inert under the open drawer: not reachable by Tab, not read out. */}
        {/* The page sits on one white rounded panel over the grey canvas
            (2026-10-10), the sidebar and header around it. */}
        <main id="main" inert={mobileOpen} className="min-w-0 flex-1 px-3 py-4 lg:px-5">
          <div className="min-h-[calc(100dvh-6rem)] rounded-2xl border border-border bg-surface px-4 py-6 shadow-[var(--shadow-card)] sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}

function Header({
  onMenuClick,
  mobileOpen,
  onSearch,
  here,
  pathname,
}: {
  onMenuClick: () => void;
  mobileOpen: boolean;
  onSearch: () => void;
  here: ReturnType<typeof locate>;
  pathname: string;
}) {
  const { me } = useAuth();
  const apple = useIsApple();

  return (
    // The indigo frame across the top, like the sidebar (2026-10-10): inside
    // `.frame-scope` the colour tokens are the frame's, so the logo, search,
    // buttons and user menu read as on a dark surface.
    <header className="frame-top frame-scope no-print sticky top-0 z-30">
      <div className="flex h-16 w-full items-center gap-3 px-4 sm:px-6">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onMenuClick}
          aria-expanded={mobileOpen}
          aria-controls="sidebar-nav"
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
        >
          {mobileOpen ? <X /> : <Menu />}
        </Button>

        {/* The COMPASS lockup (2026-10-10): the shield and the two-tone name,
            nothing under it - the bar names the product, the page says where. */}
        <Link
          href="/dashboard"
          aria-label={config.productName}
          className="group flex shrink-0 items-center gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]"
        >
          <BrandMark className="size-7 text-[var(--sidebar-badge)]" />
          <span className="leading-none">
            <span className="block text-lg font-bold tracking-tight">
              <span className="text-[var(--sidebar-badge)]">{config.productName.slice(0, 3)}</span>
              <span className="text-text">{config.productName.slice(3)}</span>
            </span>
          </span>
        </Link>

        {here && <Breadcrumb here={here} pathname={pathname} role={me?.role} />}

        <div className="flex-1" />

        {/* The palette's front door. On a phone it is an icon; on a desk it
            says what it does and how to get there without the mouse. */}
        <button
          type="button"
          onClick={onSearch}
          aria-keyshortcuts={apple ? "Meta+K" : "Control+K"}
          className={cn(
            "hidden h-9 w-64 items-center gap-2 rounded-md border border-border bg-bg px-3 text-sm text-text-subtle md:flex",
            "transition-colors hover:border-border-strong hover:text-text-muted",
            "outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]",
          )}
        >
          <Search className="size-4" aria-hidden="true" />
          {/* It finds pages and actions, not records: the name promised a search
              of projects and people that it does not do (UX review). */}
          <span className="flex-1 text-left">Jump to page…</span>
          <kbd className="rounded-md border border-border bg-bg-inset px-1.5 py-0.5 font-sans text-2xs font-medium">
            {apple ? "⌘K" : "Ctrl K"}
          </kbd>
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onSearch}
          aria-label="Jump to page"
        >
          <Search />
        </Button>

        <Button variant="ghost" size="icon" asChild>
          <HelpLink aria-label="Help manual" title="Help manual">
            <CircleHelp />
          </HelpLink>
        </Button>

        {me?.nav.includes("notifications") && (
          <Button variant="ghost" size="icon" asChild>
            <Link
              href="/notifications"
              aria-label="Notifications"
              title="Notifications"
              aria-current={pathname === "/notifications" ? "page" : undefined}
            >
              <Bell />
            </Link>
          </Button>
        )}

        <div className="ml-1 border-l border-border pl-2">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}

/** Where this page sits: its section, then its destination - a link back to
 *  the list when this is a page under it. */
function Breadcrumb({
  here,
  pathname,
  role,
}: {
  here: NonNullable<ReturnType<typeof locate>>;
  pathname: string;
  role: string | undefined;
}) {
  const atTop = pathname === here.item.href;
  const label = labelFor(here.item, role);
  return (
    <nav
      aria-label="Breadcrumb"
      className="hidden min-w-0 border-l border-border pl-3 lg:block"
    >
      <ol className="flex min-w-0 items-center gap-1.5 text-sm">
        <li className="shrink-0 text-text-subtle">{here.section.title}</li>
        <li aria-hidden="true" className="text-text-subtle">
          <ChevronRight className="size-3.5" />
        </li>
        <li className="min-w-0 truncate">
          {atTop ? (
            <span aria-current="page" className="font-medium text-text">
              {label}
            </span>
          ) : (
            <Link
              href={here.item.href}
              className="text-text-muted hover:text-text hover:underline"
            >
              {label}
            </Link>
          )}
        </li>
      </ol>
    </nav>
  );
}

function Sidebar({
  sections,
  pathname,
  mobileOpen,
  collapsed,
  onToggleCollapsed,
  onClose,
  onSignOut,
}: {
  sections: NavSection[];
  pathname: string;
  mobileOpen: boolean;
  /** Folded to icons. Desktop only: the phone drawer always shows words. */
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onClose: () => void;
  onSignOut: () => void;
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
          // The indigo frame down the left (2026-10-10), the same in both themes.
          "frame-side frame-scope no-print z-20 flex w-64 shrink-0 flex-col text-[var(--sidebar-text)]",
          "lg:sticky lg:top-16 lg:h-[calc(100dvh-4rem)] lg:transition-[width] lg:duration-200",
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
                        "group relative flex items-center gap-3 rounded-lg py-2 pr-2 pl-3 text-sm",
                        "transition-[background-color,color,box-shadow] duration-150",
                        "outline-none focus-visible:ring-2 focus-visible:ring-[var(--sidebar-badge)]",
                        folded && "lg:size-11 lg:justify-center lg:p-0",
                        // Active: a white pill on the indigo.
                        active
                          ? "bg-[var(--sidebar-active)] font-semibold text-[var(--sidebar-active-text)] shadow-[0_6px_18px_rgb(8_10_40/0.35)]"
                          : "hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text-strong)]",
                      )}
                    >
                      <Icon
                        className={cn(
                          "size-[1.125rem] shrink-0 transition-colors",
                          active
                            ? "text-accent"
                            : "text-[var(--sidebar-label)] group-hover:text-[var(--sidebar-text-strong)]",
                        )}
                        aria-hidden="true"
                      />
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
          <Tooltip content={folded ? "Sign out" : null} side="right">
          <Button
            variant="ghost"
            className={cn(
              "w-full justify-start rounded-lg px-3 text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text-strong)]",
              folded && "lg:size-11 lg:justify-center lg:px-0",
            )}
            onClick={onSignOut}
          >
            <LogOut className="size-4" aria-hidden="true" />
            <span className={cn(folded && "lg:sr-only")}>Sign out</span>
          </Button>
          </Tooltip>
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

/** Page heading with optional description and actions. Used on every page so
 *  the vertical rhythm is identical throughout. */
export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
  eyebrow,
  icon,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  /** A short kicker above the title - the section this page belongs to. */
  eyebrow?: string;
  /** The tile beside the title. Defaults to the menu item's icon on a
   *  destination's own page (2026-10-10); `null` for none. */
  icon?: React.ComponentType<{ className?: string }> | null;
}) {
  const pathname = usePathname();
  const Icon = icon === null ? undefined : (icon ?? iconForPage(pathname ?? ""));
  return (
    <div className="mb-5">
      {breadcrumb && <div className="mb-2 text-sm text-text-muted">{breadcrumb}</div>}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-4">
          {Icon && (
            <span
              aria-hidden="true"
              className="grid size-12 shrink-0 place-items-center rounded-xl border border-accent-border bg-accent-subtle text-accent-text shadow-[var(--shadow-xs)]"
            >
              {React.createElement(Icon, { className: "size-6" })}
            </span>
          )}
          <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1 text-2xs font-semibold tracking-wider text-accent-text uppercase">
              {eyebrow}
            </p>
          )}
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {/* One line on a desk (2026-10-10): a tooltip carries the whole
              sentence, and the rest is in the help. */}
          {description && (
            <p
              className="mt-1 max-w-3xl text-sm text-text-muted lg:line-clamp-1"
              title={description}
            >
              {description}
            </p>
          )}
          </div>
        </div>
        {actions && (
          <div
            className="flex max-w-full min-w-0 flex-wrap items-center gap-2"
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
        "ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-[var(--sidebar-badge)] px-1.5 text-2xs font-semibold text-[var(--sidebar-bg)]",
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
