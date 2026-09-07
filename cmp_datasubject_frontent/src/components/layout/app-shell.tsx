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
  LogOut,
  Menu,
  Moon,
  Scale,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";

import { BrandMark } from "@/components/ui/graphics";
import { Button } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { config } from "@/lib/config";
import { cn, initials } from "@/lib/format";
import { useAuth, useTheme } from "@/providers";

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
    ],
  },
  {
    title: "You",
    items: [
      { key: "notifications", href: "/notifications", label: "Notifications", icon: Bell },
      { key: "profile", href: "/account", label: "Your profile", icon: UserRound },
    ],
  },
];

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
      {/* One soft wash behind the whole shell. Fixed rather than scrolling, so
          it behaves like light in the room instead of a background image. */}
      <div aria-hidden="true" className="aurora pointer-events-none fixed inset-0 -z-10" />

      <Header onMenuClick={() => setMobileOpen(!mobileOpen)} mobileOpen={mobileOpen} />

      <div className="mx-auto flex w-full max-w-[1600px]">
        <Sidebar
          sections={sections}
          pathname={pathname}
          mobileOpen={mobileOpen}
          onClose={() => setMobileOpen(false)}
          onSignOut={signOut}
        />

        <main id="main" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}

function Header({
  onMenuClick,
  mobileOpen,
}: {
  onMenuClick: () => void;
  mobileOpen: boolean;
}) {
  const { me } = useAuth();
  const { resolved, setTheme } = useTheme();

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
          href="/my-consents"
          className="group flex items-center gap-2.5 rounded-lg font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]"
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

        <div className="flex-1" />

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
              <p className="text-sm font-medium leading-tight">{me.full_name}</p>
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

function Sidebar({
  sections,
  pathname,
  mobileOpen,
  onClose,
  onSignOut,
}: {
  sections: NavSection[];
  pathname: string;
  mobileOpen: boolean;
  onClose: () => void;
  onSignOut: () => void;
}) {
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
        className={cn(
          "no-print z-20 flex w-64 shrink-0 flex-col border-r border-border bg-surface/70",
          "lg:sticky lg:top-14 lg:h-[calc(100dvh-3.5rem)]",
          mobileOpen
            ? "fixed inset-y-14 left-0 flex overflow-y-auto bg-surface shadow-[var(--shadow-pop)]"
            : "hidden lg:flex",
        )}
      >
        <div className="flex-1 overflow-y-auto px-3 py-4">
          {sections.map((section) => (
            <div key={section.title} className="mb-5 last:mb-0">
              <p className="mb-1.5 px-3 text-2xs font-semibold uppercase tracking-wider text-text-subtle">
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
                          "group relative flex items-center gap-2.5 rounded-lg py-2 pl-3 pr-2 text-sm",
                          "transition-[background-color,color] duration-150",
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
                            active ? "text-accent" : "text-text-subtle group-hover:text-text-muted",
                          )}
                          aria-hidden="true"
                        />
                        <span className="truncate">{item.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="rule-fade shrink-0 border-t border-border p-3">
          <Button
            variant="ghost"
            className="w-full justify-start px-3 text-text-muted"
            onClick={onSignOut}
          >
            <LogOut className="size-4" aria-hidden="true" />
            Sign out
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
            <p className="mb-1 text-2xs font-semibold uppercase tracking-wider text-accent-text">
              {eyebrow}
            </p>
          )}
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description && (
            <p className="mt-1.5 max-w-2xl text-sm text-text-muted">{description}</p>
          )}
        </div>
        {actions && <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {/* A hairline that fades out to the right: it closes the header without
          drawing a hard box around every page. */}
      <div aria-hidden="true" className="rule-fade mt-5 h-px" />
    </div>
  );
}
