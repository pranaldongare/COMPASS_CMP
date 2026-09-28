/**
 * The help manual: sections numbered once and for all, narrowed by role and by
 * search, each with an anchor, and the on-screen labels marked as labels.
 */

import { describe, expect, it } from "vitest";

import { HelpManual } from "@/features/help/components/help-manual";
import type { HelpSection } from "@/features/help/types";
import { render, screen, within } from "@/test/render";

const SECTIONS: HelpSection[] = [
  {
    id: "signing-in",
    title: "Signing in",
    summary: "Password, then a code.",
    blocks: [{ kind: "steps", items: ["Click [[Sign in]].", "Type the code."] }],
  },
  {
    id: "exports",
    title: "Exports",
    summary: "The file of people.",
    roles: ["dpo", "dco"],
    blocks: [{ kind: "warning", text: "Refused if a processor has no country." }],
  },
  {
    id: "users",
    title: "Staff accounts",
    summary: "Provisioning.",
    roles: ["admin"],
    blocks: [
      { kind: "faq", items: [{ q: "Where is the invitation?", a: "In the outbox." }] },
    ],
  },
];

const ROLES = [
  { value: "dpo", label: "DPO" },
  { value: "dco", label: "DCO" },
  { value: "admin", label: "Administrator" },
];

function renderManual(initialRole = "") {
  return render(
    <HelpManual
      product="COMPASS CMP"
      intro="How to use it."
      sections={SECTIONS}
      roles={ROLES}
      initialRole={initialRole}
      contact={<p>Contact us</p>}
    />,
  );
}

function sectionTitles(): string[] {
  return screen
    .getAllByRole("heading", { level: 2 })
    .map((h) => h.textContent ?? "")
    .filter((t) => t !== "Contact us");
}

describe("HelpManual", () => {
  it("numbers every section and gives each an anchor", () => {
    renderManual();
    expect(sectionTitles()).toEqual(["1. Signing in", "2. Exports", "3. Staff accounts"]);
    expect(screen.getByRole("link", { name: "Exports" })).toHaveAttribute(
      "href",
      "#exports",
    );
    expect(document.getElementById("users")).not.toBeNull();
  });

  it("opens filtered to the reader's role, keeping each section's number", () => {
    renderManual("dco");
    expect(sectionTitles()).toEqual(["1. Signing in", "2. Exports"]);
    expect(screen.getByText("2 of 3 sections for the DCO")).toBeInTheDocument();
  });

  it("shows every section when 'Every role' is chosen", async () => {
    const { user } = renderManual("admin");
    expect(sectionTitles()).toEqual(["1. Signing in", "3. Staff accounts"]);

    await user.selectOptions(screen.getByLabelText("Show sections for"), "");
    expect(sectionTitles()).toHaveLength(3);
  });

  it("searches every word of a section, including its steps and answers", async () => {
    const { user } = renderManual();
    const box = screen.getByRole("searchbox", { name: "Search the manual" });

    await user.type(box, "outbox");
    expect(sectionTitles()).toEqual(["3. Staff accounts"]);

    await user.clear(box);
    await user.type(box, "no country");
    expect(sectionTitles()).toEqual(["2. Exports"]);
  });

  it("says so when nothing matches, and offers every section back", async () => {
    const { user } = renderManual("dpo");
    await user.type(screen.getByRole("searchbox"), "zebra");
    expect(screen.getByText("Nothing in the manual matches")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show every section" }));
    expect(sectionTitles()).toHaveLength(3);
    expect(screen.getByRole("searchbox")).toHaveValue("");
  });

  it("marks on-screen labels, and numbers the steps", () => {
    renderManual();
    const section = document.getElementById("signing-in") as HTMLElement;
    const label = within(section).getByText("Sign in");
    expect(label.tagName).toBe("SPAN");
    expect(within(section).getByText("Step 1:", { exact: false })).toBeInTheDocument();
  });
});
