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
  ChevronRight,
  LogOut,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Sun,
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
import { labelFor, locate, sectionsFor, type NavSection } from "@/components/layout/nav";
import { BrandMark } from "@/components/ui/graphics";
import { Button } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { config } from "@/lib/config";
import { cn, initials } from "@/lib/format";
import { useMyTickets, useRequestsAttention } from "@/features/rights/queries";
import { useAuth, useTheme } from "@/providers";

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

      <div className="mx-auto flex w-full max-w-[1600px]">
        <Sidebar
          sections={sections}
          pathname={pathname}
          mobileOpen={mobileOpen}
          collapsed={collapsed}
          onToggleCollapsed={() => setCollapsed(!collapsed)}
          onClose={() => setMobileOpen(false)}
          onSignOut={signOut}
        />

        <main id="main" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
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
  const { resolved, setTheme } = useTheme();
  const apple = useIsApple();

  return (
    <header className="glass no-print sticky top-0 z-30 border-b border-border">
      <div className="mx-auto flex h-14 w-full max-w-[1600px] items-center gap-3 px-4 sm:px-6 lg:px-8">
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

        <Link
          href="/dashboard"
          className="group flex shrink-0 items-center gap-2.5 rounded-lg font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]"
        >
          <span className="brand-gradient grid size-8 place-items-center rounded-lg shadow-[var(--shadow-sm)] transition-shadow group-hover:shadow-[var(--shadow-glow)]">
            <BrandMark className="size-5 text-white" />
          </span>
          <span className="hidden leading-tight sm:block">
            <span className="block text-sm">{config.appName}</span>
            <span className="block text-2xs font-normal text-text-subtle">
              DPDP Act 2023
            </span>
          </span>
          <span className="text-sm sm:hidden">CMP</span>
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
            "hidden h-9 w-60 items-center gap-2 rounded-lg border border-border bg-surface/70 px-3 text-sm text-text-subtle md:flex",
            "shadow-[var(--shadow-sm)] transition-colors hover:border-border-strong hover:text-text-muted",
            "outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]",
          )}
        >
          <Search className="size-4" aria-hidden="true" />
          <span className="flex-1 text-left">Search or jump to…</span>
          <kbd className="rounded-md border border-border bg-bg-inset px-1.5 py-0.5 font-sans text-2xs font-medium">
            {apple ? "⌘K" : "Ctrl K"}
          </kbd>
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onSearch}
          aria-label="Search or jump to"
        >
          <Search />
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

        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(resolved === "dark" ? "light" : "dark")}
          aria-label={`Switch to ${resolved === "dark" ? "light" : "dark"} theme`}
          title={`Switch to ${resolved === "dark" ? "light" : "dark"} theme`}
        >
          {resolved === "dark" ? <Sun /> : <Moon />}
        </Button>

        {me && (
          <div className="flex items-center gap-2.5 border-l border-border pl-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm leading-tight font-medium">{me.full_name}</p>
              <StatusBadge kind="role" value={me.role} dot={false} className="mt-0.5" />
            </div>
            <span
              className="grid size-9 place-items-center rounded-full bg-accent-subtle text-xs font-semibold text-accent-text ring-1 ring-accent-border/60"
              aria-hidden="true"
            >
              {initials(me.full_name)}
            </span>
          </div>
        )}
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
  return (
    <>
      {/* Scrim. Clicking it closes the drawer; it is hidden from assistive tech
          because the close button in the header already does the job. */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 backdrop-blur-[2px] lg:hidden"
          aria-hidden="true"
          onClick={onClose}
        />
      )}

      <nav
        id="sidebar-nav"
        aria-label="Main"
        data-collapsed={folded || undefined}
        className={cn(
          "no-print z-20 flex w-64 shrink-0 flex-col border-r border-border bg-surface/70",
          "lg:sticky lg:top-14 lg:h-[calc(100dvh-3.5rem)] lg:transition-[width] lg:duration-200",
          folded && "lg:w-[4.25rem]",
          mobileOpen
            ? "fixed inset-y-14 left-0 flex overflow-y-auto bg-surface shadow-[var(--shadow-pop)]"
            : "hidden lg:flex",
        )}
      >
        <div
          className={cn(
            "flex-1 overflow-x-hidden overflow-y-auto py-4",
            folded ? "lg:px-2.5" : "px-3",
          )}
        >
          {sections.map((section, i) => (
            <div key={section.title} className="mb-5 last:mb-0">
              <p
                className={cn(
                  "mb-1.5 px-3 text-2xs font-semibold tracking-wider text-text-subtle uppercase",
                  folded && "lg:sr-only",
                )}
              >
                {section.title}
              </p>
              {/* Folded, a hairline stands in for the heading so the groups
                  still read as groups. */}
              {folded && i > 0 && (
                <div
                  aria-hidden="true"
                  className="mx-2 mb-2 hidden h-px bg-border lg:block"
                />
              )}
              <ul className="space-y-0.5">
                {section.items.map((item) => {
                  const active =
                    pathname === item.href || pathname.startsWith(`${item.href}/`);
                  const Icon = item.icon;
                  const label = labelFor(item, me?.role);
                  return (
                    <li key={`${section.title}:${item.href}`}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        // Folded, the word is visually hidden but still the
                        // link's name; the tooltip is for sighted mouse users.
                        title={folded ? label : undefined}
                        className={cn(
                          "group relative flex items-center gap-2.5 rounded-lg py-2 pr-2 pl-3 text-sm",
                          "transition-[background-color,color] duration-150",
                          folded && "lg:justify-center lg:px-0",
                          active
                            ? "bg-accent-subtle font-medium text-accent-text"
                            : "text-text-muted hover:bg-bg-inset hover:text-text",
                        )}
                      >
                        {/* The rail. Position is the primary signal here -
                            colour alone would not survive greyscale, and
                            aria-current carries it for screen readers. */}
                        <span
                          aria-hidden="true"
                          className={cn(
                            "absolute inset-y-1.5 left-0 w-0.5 rounded-full transition-opacity",
                            active
                              ? "brand-gradient opacity-100"
                              : "bg-border-strong opacity-0 group-hover:opacity-100",
                          )}
                        />
                        <Icon
                          className={cn(
                            "size-4 shrink-0 transition-colors",
                            active
                              ? "text-accent"
                              : "text-text-subtle group-hover:text-text-muted",
                          )}
                          aria-hidden="true"
                        />
                        <span className={cn("truncate", folded && "lg:sr-only")}>
                          {label}
                        </span>
                        {item.key === "tickets" && <TicketsBadge folded={folded} />}
                        {item.key === "requests" && <RequestsBadge folded={folded} />}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div
          className={cn(
            "rule-fade shrink-0 space-y-0.5 border-t border-border",
            folded ? "lg:p-2.5" : "p-3",
          )}
        >
          <Button
            variant="ghost"
            className={cn(
              "hidden w-full justify-start px-3 text-text-muted lg:flex",
              folded && "lg:justify-center lg:px-0",
            )}
            onClick={onToggleCollapsed}
            aria-expanded={!folded}
            aria-controls="sidebar-nav"
            title={folded ? "Expand sidebar" : undefined}
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
          <Button
            variant="ghost"
            className={cn(
              "w-full justify-start px-3 text-text-muted",
              folded && "lg:justify-center lg:px-0",
            )}
            onClick={onSignOut}
            title={folded ? "Sign out" : undefined}
          >
            <LogOut className="size-4" aria-hidden="true" />
            <span className={cn(folded && "lg:sr-only")}>Sign out</span>
          </Button>
        </div>
      </nav>
    </>
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
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  /** A short kicker above the title - the section this page belongs to. */
  eyebrow?: string;
}) {
  return (
    <div className="mb-6">
      {breadcrumb && <div className="mb-2 text-sm text-text-muted">{breadcrumb}</div>}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1 text-2xs font-semibold tracking-wider text-accent-text uppercase">
              {eyebrow}
            </p>
          )}
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description && (
            <p className="mt-1.5 max-w-2xl text-sm text-text-muted">{description}</p>
          )}
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
      {/* A hairline that fades out to the right: it closes the header without
          drawing a hard box around every page. */}
      <div aria-hidden="true" className="rule-fade mt-5 h-px" />
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
        "ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-2xs font-semibold text-white",
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
