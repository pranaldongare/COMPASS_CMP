/**
 * Tabs, the dropdown menu and the collapsible card: the keyboard and the
 * attributes assistive technology reads, which are the parts easy to break
 * without seeing it.
 */

import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CollapsibleCard } from "@/components/ui/collapsible";
import { Menu, MenuItem, MenuLabel } from "@/components/ui/menu";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import { describeAgent } from "@/features/account/components/sessions-card";
import { render, screen } from "@/test/render";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function AccountTabs() {
  const [tab, setTab] = useHashTab(
    ["contacts", "sessions", "password"] as const,
    "contacts",
  );
  return (
    <Tabs value={tab} onValueChange={setTab} label="Your account">
      <TabList>
        <Tab value="contacts">Contacts</Tab>
        <Tab value="sessions" count={3}>
          Sessions
        </Tab>
        <Tab value="password">Password</Tab>
      </TabList>
      <TabPanel value="contacts">
        <input aria-label="Draft" />
      </TabPanel>
      <TabPanel value="sessions">Three sessions</TabPanel>
      <TabPanel value="password">Change it</TabPanel>
    </Tabs>
  );
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  localStorage.clear();
});

describe("Tabs", () => {
  it("wires tabs to panels and shows only the selected one", () => {
    render(<AccountTabs />);
    const tab = screen.getByRole("tab", { name: /Sessions/ });
    expect(screen.getByRole("tablist", { name: "Your account" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Contacts" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(tab).toHaveAttribute("aria-selected", "false");
    expect(tab).toHaveTextContent("3");
    expect(screen.getByText("Three sessions")).not.toBeVisible();
  });

  it("moves with the arrow keys, Home and End, keeping one tab stop", async () => {
    const { user } = render(<AccountTabs />);
    await user.click(screen.getByRole("tab", { name: "Contacts" }));

    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /Sessions/ })).toHaveFocus();
    expect(screen.getByText("Three sessions")).toBeVisible();
    expect(screen.getByRole("tab", { name: "Contacts" })).toHaveAttribute("tabindex", "-1");

    await user.keyboard("{End}");
    expect(screen.getByText("Change it")).toBeVisible();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Contacts" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}{Home}");
    expect(screen.getByRole("tab", { name: "Contacts" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("keeps the tab in the address, and keeps a hidden panel's input", async () => {
    const { user } = render(<AccountTabs />);
    await user.type(screen.getByLabelText("Draft"), "half typed");

    await user.click(screen.getByRole("tab", { name: "Password" }));
    expect(window.location.hash).toBe("#password");

    await user.click(screen.getByRole("tab", { name: "Contacts" }));
    expect(screen.getByLabelText("Draft")).toHaveValue("half typed");
  });

  it("opens on the tab the address names, and ignores one it does not know", () => {
    window.history.replaceState(null, "", "/#sessions");
    const { unmount } = render(<AccountTabs />);
    expect(screen.getByRole("tab", { name: /Sessions/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    unmount();

    window.history.replaceState(null, "", "/#nonsense");
    render(<AccountTabs />);
    expect(screen.getByRole("tab", { name: "Contacts" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});

describe("Menu", () => {
  function AccountMenu({ onSignOut }: { onSignOut: () => void }) {
    return (
      <>
        <Menu label="Account menu" trigger="PM">
          <MenuLabel>Priya Menon</MenuLabel>
          <MenuItem href="/account">Your profile</MenuItem>
          <MenuItem onSelect={() => {}}>Switch theme</MenuItem>
          <MenuItem onSelect={onSignOut}>Sign out</MenuItem>
        </Menu>
        <button>Elsewhere</button>
      </>
    );
  }

  it("opens on the first item and moves with the arrow keys", async () => {
    const { user } = render(<AccountMenu onSignOut={() => {}} />);
    const trigger = screen.getByRole("button", { name: "Account menu" });
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("menuitem", { name: "Your profile" })).toHaveFocus();

    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Switch theme" })).toHaveFocus();
    await user.keyboard("{End}{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Your profile" })).toHaveFocus();
  });

  it("closes on Escape and gives focus back to the trigger", async () => {
    const { user } = render(<AccountMenu onSignOut={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Account menu" })).toHaveFocus();
  });

  it("runs an item and closes; a press elsewhere closes it too", async () => {
    const signOut = vi.fn();
    const { user } = render(<AccountMenu onSignOut={signOut} />);
    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(screen.getByRole("menuitem", { name: "Sign out" }));
    expect(signOut).toHaveBeenCalledOnce();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(screen.getByRole("button", { name: "Elsewhere" }));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});

describe("CollapsibleCard", () => {
  it("folds its body away and says so", async () => {
    const { user } = render(
      <CollapsibleCard title="History">
        <p>Pending → Approved</p>
      </CollapsibleCard>,
    );
    const toggle = screen.getByRole("button", { name: /History/ });
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Pending → Approved")).not.toBeVisible();
  });

  it("remembers the choice under its key", async () => {
    const card = (
      <CollapsibleCard title="Clock and path" storageKey="test.overview">
        <p>The path</p>
      </CollapsibleCard>
    );
    const { user, unmount } = render(card);
    await user.click(screen.getByRole("button", { name: /Clock and path/ }));
    unmount();

    render(card);
    expect(screen.getByRole("button", { name: /Clock and path/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
});

describe("describeAgent", () => {
  it("names the browser and the system", () => {
    expect(
      describeAgent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36",
      ),
    ).toBe("Chrome on macOS");
    expect(
      describeAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
      ),
    ).toBe("Firefox on Windows");
    expect(describeAgent("python-httpx/0.28.1")).toBe("python-httpx");
    expect(describeAgent(null)).toBe("Unknown client");
  });
});
