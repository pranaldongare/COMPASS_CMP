/**
 * The account menu at the right of the header: who you are, your profile, the
 * manual, the theme, and signing out - the things that are about you rather
 * than about the page.
 *
 * Sign out stays in the sidebar as well. It is the one action somebody must
 * find without thinking, and two places for it cost nothing.
 */
"use client";

import { BookOpen, LogOut, Moon, Sun, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";

import { helpHref } from "@/components/layout/help-link";
import { Menu, MenuItem, MenuLabel, MenuSeparator } from "@/components/ui/menu";
import { StatusBadge } from "@/components/ui/status";
import { initials } from "@/lib/format";
import { useAuth, useTheme } from "@/providers";

export function UserMenu() {
  const { me, signOut } = useAuth();
  const { resolved, setTheme } = useTheme();
  const router = useRouter();
  if (!me) return null;
  const next = resolved === "dark" ? "light" : "dark";

  return (
    <Menu
      label={`Account menu for ${me.full_name}`}
      // Just the initials in the bar (2026-10-10): the name and role are in
      // the menu it opens, and the button's name says whose it is.
      triggerClassName="group rounded-full p-0.5 hover:bg-bg-inset"
      trigger={
        <span
          aria-hidden="true"
          title={me.full_name}
          className="grid size-9 place-items-center rounded-full bg-accent-subtle text-xs font-semibold text-accent-text ring-1 ring-accent-border/60 transition-shadow group-hover:ring-accent-border group-aria-expanded:ring-2"
        >
          {initials(me.full_name)}
        </span>
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
