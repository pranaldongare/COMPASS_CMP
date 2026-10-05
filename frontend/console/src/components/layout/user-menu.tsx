/**
 * The account menu at the right of the header: who you are, your profile, the
 * manual, the theme, and signing out - the things that are about you rather
 * than about the page.
 *
 * Sign out stays in the sidebar as well. It is the one action somebody must
 * find without thinking, and two places for it cost nothing.
 */
"use client";

import { BookOpen, ChevronDown, LogOut, Moon, Sun, UserRound } from "lucide-react";
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
      triggerClassName="group flex items-center gap-2.5 py-1 pr-1 pl-2 hover:bg-bg-inset"
      trigger={
        <>
          <span className="hidden text-right sm:block">
            <span className="block text-sm leading-tight font-medium">{me.full_name}</span>
            <StatusBadge kind="role" value={me.role} dot={false} className="mt-0.5" />
          </span>
          <span
            aria-hidden="true"
            className="grid size-9 place-items-center rounded-full bg-accent-subtle text-xs font-semibold text-accent-text ring-1 ring-accent-border/60"
          >
            {initials(me.full_name)}
          </span>
          <ChevronDown
            aria-hidden="true"
            className="size-4 text-text-subtle transition-transform group-aria-expanded:rotate-180"
          />
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
          Your profile
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
