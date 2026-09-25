/**
 * The command palette.
 *
 * The property that matters most is the same one the sidebar keeps: nothing is
 * offered that the server did not put in `me.nav`. A palette that listed every
 * page and relied on the page to refuse would be a menu of 403s.
 */

import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  CommandPalette,
  rememberVisit,
  useCommandPaletteShortcut,
} from "@/components/layout/command-palette";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import type { Me } from "@/types";

const push = vi.fn();
const signOut = vi.fn();
const setTheme = vi.fn();
let currentMe: Me = makeMe();

let pathname = "/dashboard";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => pathname,
}));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: currentMe, signOut }),
  useTheme: () => ({ resolved: "light", setTheme }),
}));

function Harness() {
  const [open, setOpen] = React.useState(false);
  const toggle = React.useCallback(() => setOpen((o) => !o), []);
  useCommandPaletteShortcut(toggle);
  return <CommandPalette open={open} onOpenChange={setOpen} />;
}

function optionNames(): string[] {
  return screen.getAllByRole("option").map((o) => o.textContent ?? "");
}

beforeEach(() => {
  push.mockReset();
  signOut.mockReset();
  setTheme.mockReset();
  localStorage.clear();
  pathname = "/dashboard";
  currentMe = makeMe({ role: "dco", nav: ["dashboard", "projects", "links", "profile"] });
});

describe("CommandPalette", () => {
  it("opens on Ctrl+K and offers only the destinations the server granted", async () => {
    const { user } = render(<Harness />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.keyboard("{Control>}k{/Control}");

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    const names = optionNames();
    expect(names).toEqual(
      expect.arrayContaining(["Dashboard", "Projects", "Consent links", "Your profile"]),
    );
    expect(names.join(" ")).not.toMatch(/Audit trail|Users|Rights requests/);
  });

  it("filters as you type and opens the highlighted page with Enter", async () => {
    const { user } = render(<Harness />);
    await user.keyboard("{Meta>}k{/Meta}");

    await user.type(screen.getByRole("combobox"), "link");
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent("Consent links");

    await user.keyboard("{Enter}");
    expect(push).toHaveBeenCalledWith("/links");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("matches the other words a page is known by", async () => {
    const { user } = render(<Harness />);
    await user.keyboard("{Control>}k{/Control}");

    await user.type(screen.getByRole("combobox"), "study");
    expect(optionNames()[0]).toMatch(/^Projects/);
  });

  it("moves the highlight with the arrow keys without moving focus", async () => {
    const { user } = render(<Harness />);
    await user.keyboard("{Control>}k{/Control}");
    const input = screen.getByRole("combobox");
    const first = input.getAttribute("aria-activedescendant");

    await user.keyboard("{ArrowDown}");

    expect(input).toHaveFocus();
    expect(input.getAttribute("aria-activedescendant")).not.toBe(first);
    const selected = screen.getAllByRole("option", { selected: true });
    expect(selected).toHaveLength(1);
    expect(selected[0].id).toBe(input.getAttribute("aria-activedescendant"));
  });

  it("says so when nothing matches", async () => {
    const { user } = render(<Harness />);
    await user.keyboard("{Control>}k{/Control}");

    await user.type(screen.getByRole("combobox"), "zzz");
    expect(screen.queryAllByRole("option")).toHaveLength(0);
    expect(screen.getByText(/Nothing matches/)).toBeInTheDocument();
  });

  it("lists recent pages first, but never one the person can no longer open", async () => {
    rememberVisit("/audit");
    rememberVisit("/projects");
    const { user } = render(<Harness />);
    await user.keyboard("{Control>}k{/Control}");

    const recent = screen.getByRole("group", { name: "Recent" });
    expect(recent).toHaveTextContent("Projects");
    expect(recent).not.toHaveTextContent("Audit trail");
  });

  it("does not offer the page you are on as a recent one", async () => {
    rememberVisit("/links");
    rememberVisit("/projects");
    pathname = "/projects/some-project";
    const { user } = render(<Harness />);
    await user.keyboard("{Control>}k{/Control}");

    const recent = screen.getByRole("group", { name: "Recent" });
    expect(recent).toHaveTextContent("Consent links");
    expect(recent).not.toHaveTextContent("Projects");
  });

  it("signs out from the actions", async () => {
    const { user } = render(<Harness />);
    await user.keyboard("{Control>}k{/Control}");

    await user.type(screen.getByRole("combobox"), "sign out");
    await user.keyboard("{Enter}");
    expect(signOut).toHaveBeenCalledOnce();
  });
});
