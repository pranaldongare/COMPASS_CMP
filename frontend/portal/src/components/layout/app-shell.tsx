/**
 * The authenticated shell: sidebar, header, content region.
 *
 * This is the data principal's portal, so the only destinations are her own:
 * her consents, her rights requests, her notifications and her profile. Each
 * is still gated on `me.nav`, which the server computes from the permission
 * matrix - the frontend does not decide who sees what, it only knows where
 * each key leads in this deployment.
 *
 * The sidebar groups those destinations into sections. A section renders only
 * when the server has granted at least one item inside it.
 */
"use client";

import {
  Bell,
  FileText,
  House,
  Menu,
  Scale,
  UserRound,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";

import { PillTrail, type Crumb } from "@/components/layout/pill-trail";
import { useDrawer } from "@/components/layout/use-drawer";
import { UserMenu } from "@/components/layout/user-menu";
import { BrandMark } from "@/components/ui/graphics";
import { Button } from "@/components/ui/primitives";
import { config } from "@/lib/config";
import { cn } from "@/lib/format";
import { useAuth } from "@/providers";

interface NavItem {
  /** Must match a value in `me.nav`, which the server computes from the
   *  permission matrix. Anything not in that list is not rendered. */
  key: string;
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const SECTIONS: NavSection[] = [
  {
    title: "Your data",
    items: [
      // The server's "consents" and "requests" keys. On the staff console the
      // same keys lead to the registers; here they lead to her own records.
      { key: "consents", href: "/my-consents", label: "My consents", icon: FileText },
      { key: "requests", href: "/my-requests", label: "My requests", icon: Scale },
      // Granted with requests: a nomination is the right to have a request
      // made for you (s.14). Its own page, not the foot of My requests.
      { key: "requests", href: "/my-nominations", label: "My nominations", icon: UserRound },
      // The full list behind the header's bell. "My profile" is in the
      // account menu, with sign-out (UX review 2026-10-05).
      { key: "notifications", href: "/notifications", label: "Updates", icon: Bell },
    ],
  },
];

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

  // The server says which sections this account has; nothing renders that it
  // did not grant.
  const sections = SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => me?.nav.includes(item.key)),
  })).filter((section) => section.items.length > 0);

  return (
    // Deliberately no background on this element: `body` already paints the
    // page colour, and a second opaque layer here would sit on top of the wash
    // below and hide it.
    <div className="relative min-h-dvh">
      {/* No top bar on a desk (2026-10-10): the sidebar carries the logo and
          the settings menu. A phone keeps a slim bar, since its sidebar is a
          closed drawer. */}
      <MobileBar onMenuClick={() => setMobileOpen(!mobileOpen)} mobileOpen={mobileOpen} />

      <div className="flex w-full">
        <Sidebar
          sections={sections}
          pathname={pathname}
          mobileOpen={mobileOpen}
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
    </div>
  );
}

/** The COMPASS lockup, as on the sign-in screen and the console. */
function Lockup() {
  return (
    <Link
      href="/my-consents"
      aria-label={config.productName}
      className="group flex items-center gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]"
    >
      <BrandMark className="size-7 text-accent-text" />
      <span className="block text-lg leading-none font-bold tracking-tight">
        <span className="text-accent-text">{config.productName.slice(0, 3)}</span>
        <span className="text-text-muted">{config.productName.slice(3)}</span>
      </span>
    </Link>
  );
}

/** A phone's bar: the drawer's button, the logo and the account circle. Gone
 *  from `lg` up, where the sidebar carries all of it. */
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
  onClose,
}: {
  sections: NavSection[];
  pathname: string;
  mobileOpen: boolean;
  onClose: () => void;
}) {
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
        className={cn(
          // Line (2026-10-10): white down the left, white in both themes.
          "frame-light sidebar-glow no-print z-20 flex w-64 shrink-0 flex-col border-r border-border bg-[var(--sidebar-bg)] text-[var(--sidebar-text)]",
          "lg:sticky lg:top-0 lg:h-dvh",
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
        {/* The head (2026-10-10): the logo. The phone bar carries it below lg. */}
        <div className="hidden h-16 shrink-0 items-center px-5 lg:flex">
          <Lockup />
        </div>
        <div className="sidebar-scroll flex-1 overflow-y-auto px-3 py-4">
          {sections.map((section, i) => (
            <div key={section.title} className="mb-5 last:mb-0">
              <p className="mb-1.5 px-3 text-2xs font-semibold uppercase tracking-wider text-[var(--sidebar-label)]">
                {section.title}
              </p>
              <ul className="space-y-0.5">
                {section.items.map((item) => {
                  const active =
                    pathname === item.href || pathname.startsWith(`${item.href}/`);
                  const Icon = item.icon;
                  return (
                    <li key={`${section.title}:${item.href}`}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "group relative flex items-center gap-3 rounded-xl py-1.5 pr-2 pl-1.5 text-sm",
                          "transition-[background-color,color,box-shadow] duration-150",
                          "outline-none focus-visible:ring-2 focus-visible:ring-[var(--sidebar-badge)]",
                          // Active: a blue gradient pill (.nav-current), white text.
                          active
                            ? "nav-current font-semibold"
                            : "hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text-strong)]",
                        )}
                      >
                        <span aria-hidden="true" className={`nav-tile nav-tint-${i % 4}`}>
                          <Icon className="size-4" />
                        </span>
                        <span className="truncate">{item.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* The settings menu at the very end: profile, manual, theme and
            signing out (2026-10-10). */}
        <div className="shrink-0 border-t border-[var(--sidebar-border)] p-3">
          <UserMenu placement="sidebar" />
        </div>
      </nav>
    </>
  );
}

/** The steps to this page from My consents, the portal's home: the menu
 *  destination it sits under, then the page itself when it is a record under
 *  it. None on the home page. */
function trailFor(pathname: string, title: string): Crumb[] {
  if (pathname === "/my-consents" || pathname === "/") return [];
  const home: Crumb = { label: "My consents", href: "/my-consents", icon: House };
  const dest = SECTIONS.flatMap((s) => s.items)
    .filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0];
  if (!dest) return [home, { label: title }];
  if (dest.href === pathname) return [home, { label: dest.label, icon: dest.icon }];
  return [home, { label: dest.label, href: dest.href, icon: dest.icon }, { label: title }];
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
  const pathname = usePathname() ?? "";
  const fromMenu = SECTIONS.flatMap((s) => s.items).find((item) => item.href === pathname)?.icon;
  const Icon = icon === null ? undefined : (icon ?? fromMenu);
  const crumbs = trailFor(pathname, title);
  return (
    <div className="mb-5">
      {/* The pill trail (2026-10-10); a page's own back link at its end. */}
      <PillTrail crumbs={crumbs} extra={breadcrumb} />
      {/* On a desk the actions keep their place at the right (2026-10-10):
          the heading gives way - its line clamps - rather than pushing them
          down under it. */}
      <div className="flex flex-wrap items-start justify-between gap-3 lg:flex-nowrap">
        <div className="flex min-w-0 items-start gap-4 lg:flex-1">
          {Icon && (
            <span
              aria-hidden="true"
              className="grid size-12 shrink-0 place-items-center rounded-xl border border-accent-border bg-accent-subtle text-accent-text shadow-[var(--shadow-xs)]"
            >
              <Icon className="size-6" />
            </span>
          )}
          <div className="min-w-0">
            {eyebrow && (
              <p className="mb-1 text-2xs font-semibold uppercase tracking-wider text-accent-text">
                {eyebrow}
              </p>
            )}
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {description && (
              <p className="mt-1 max-w-3xl text-sm text-text-muted">{description}</p>
            )}
          </div>
        </div>
        {actions && <div className="flex max-w-full min-w-0 flex-wrap items-center gap-2 lg:shrink-0 lg:flex-nowrap">{actions}</div>}
      </div>
    </div>
  );
}
