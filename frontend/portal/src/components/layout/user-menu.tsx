/**
 * The account menu - "Settings": who you are, your profile, the manual, the
 * theme, and signing out - the things that are about you rather than about
 * the page.
 *
 * At the foot of the sidebar on a desk (2026-10-10, when the top bar went),
 * opening upwards; in the slim bar a phone keeps, as the initials alone.
 */
"use client";

import { BookOpen, ChevronsUpDown, LogOut, Moon, Sun, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";

import { helpHref } from "@/components/layout/help-link";
import { Menu, MenuItem, MenuLabel, MenuSeparator } from "@/components/ui/menu";
import { StatusBadge } from "@/components/ui/status";
import { cn, initials } from "@/lib/format";
import { useAuth, useTheme } from "@/providers";

export function UserMenu({
  placement = "bar",
  folded = false,
}: {
  /** `sidebar`: a full-width row at the foot of the sidebar, opening upwards. */
  placement?: "bar" | "sidebar";
  /** The sidebar folded to icons: the circle alone. */
  folded?: boolean;
} = {}) {
  const { me, signOut } = useAuth();
  const { resolved, setTheme } = useTheme();
  const router = useRouter();
  if (!me) return null;
  const next = resolved === "dark" ? "light" : "dark";

  return (
    <Menu
      label={`Account menu for ${me.full_name}`}
      side={placement === "sidebar" ? "top" : "bottom"}
      align={placement === "sidebar" ? "start" : "end"}
      triggerClassName={
        placement === "sidebar"
          ? cn(
              "group flex w-full items-center gap-3 rounded-lg p-1.5 text-left text-sm hover:bg-[var(--sidebar-hover)]",
              folded && "lg:size-11 lg:justify-center lg:p-0",
            )
          : "group rounded-full p-0.5 hover:bg-bg-inset"
      }
      trigger={
        <>
          <span
            aria-hidden="true"
            title={me.full_name}
            className="grid size-9 shrink-0 place-items-center rounded-full bg-accent-subtle text-xs font-semibold text-accent-text ring-1 ring-accent-border/60 transition-shadow group-hover:ring-accent-border group-aria-expanded:ring-2"
          >
            {initials(me.full_name)}
          </span>
          {placement === "sidebar" && (
            <>
              <span
                aria-hidden="true"
                className={cn("flex-1 font-medium text-[var(--sidebar-text-strong)]", folded && "lg:hidden")}
              >
                Settings
              </span>
              <ChevronsUpDown
                aria-hidden="true"
                className={cn("size-4 text-[var(--sidebar-label)]", folded && "lg:hidden")}
              />
            </>
          )}
        </>
      }
    >
      <MenuLabel>
        <p className="truncate text-sm font-semibold">{me.full_name}</p>
        <StatusBadge kind="role" value={me.role} dot={false} className="mt-1" />
      </MenuLabel>
      <MenuSeparator />
      {me.nav.includes("profile") && (
        <MenuItem href="/account" icon={UserRound}>
          My profile
        </MenuItem>
      )}
      <MenuItem onSelect={() => router.push(helpHref())} icon={BookOpen}>
        Help manual
      </MenuItem>
      <MenuItem onSelect={() => setTheme(next)} icon={resolved === "dark" ? Sun : Moon}>
        Switch to {next} theme
      </MenuItem>
      <MenuSeparator />
      <MenuItem onSelect={signOut} icon={LogOut} tone="danger">
        Sign out
      </MenuItem>
    </Menu>
  );
}
