/**
 * Each role's sidebar starts with its daily work (UX review 2026-10-05).
 *
 * The sidebar listed every section in one fixed order for everybody: a DPO's
 * rights requests came after governance, consent, registry and data movement,
 * and their own tickets lower still. Each role now opens with its own short
 * list, in the order its work runs; the rest follows in the usual groups.
 * Profile and notifications live in the account menu and the bell.
 */
import { describe, expect, it } from "vitest";

import { labelFor, sidebarFor } from "@/components/layout/nav";
import type { Me } from "@/types";

const NAV: Record<string, string[]> = {
  dpo: ["dashboard", "projects", "approvals", "notices", "purposes", "sites", "collections", "processors", "sources", "consents", "links", "exports", "imports", "requests", "breaches", "audit", "users", "messages", "delegate", "tickets", "notifications", "profile"],
  rnd_user: ["dashboard", "projects", "notices", "processors", "approvals", "imports", "collections", "tickets", "notifications", "profile"],
  dco_admin: ["dashboard", "projects", "sites", "sources", "links", "consents", "exports", "imports", "collections", "delegate", "tickets", "notifications", "profile"],
  dco: ["dashboard", "projects", "sites", "sources", "links", "consents", "exports", "imports", "collections", "delegate", "tickets", "notifications", "profile"],
  admin: ["dashboard", "users", "messages", "processors", "sources", "requests", "audit", "delegate", "tickets", "notifications", "profile"],
};

function me(role: string): Me {
  return { role, nav: NAV[role] ?? NAV.dco } as unknown as Me;
}

function first(role: string): string[] {
  const [work] = sidebarFor(me(role));
  return work.items.map((item) => labelFor(item, role));
}

describe("sidebarFor", () => {
  it.each([
    ["dpo", ["Dashboard", "Rights requests", "Breaches", "My tasks", "Projects", "Notices"]],
    ["rnd_user", ["Dashboard", "My projects", "Approval documents", "My tasks", "Notices"]],
    ["dco_admin", ["Dashboard", "Collection sites", "Data sources", "My tasks", "Consent links", "Projects"]],
    ["dco", ["Dashboard", "My projects", "Collection sites", "Consent links", "My tasks", "Collections"]],
    ["rco", ["Dashboard", "My projects", "Collection sites", "Consent links", "My tasks", "Collections"]],
    ["admin", ["Dashboard", "Users", "Grievances about the DPO", "Message templates", "Processors", "Data sources", "Audit trail"]],
  ])("opens %s's sidebar with its daily work", (role, expected) => {
    expect(first(role)).toEqual(expected);
  });

  it("lists every other granted page once, below, and nothing it did not grant", () => {
    for (const role of Object.keys(NAV)) {
      const all = sidebarFor(me(role)).flatMap((s) => s.items.map((i) => i.key));
      expect(new Set(all).size).toBe(all.length);
      const expected = NAV[role].filter((k) => k !== "profile" && k !== "notifications");
      expect([...all].sort()).toEqual([...expected].sort());
    }
  });

  it("names the pages by what they hold", () => {
    const labels = sidebarFor(me("dpo")).flatMap((s) => s.items.map((i) => labelFor(i, "dpo")));
    expect(labels).toEqual(
      expect.arrayContaining(["Approval documents", "Message templates", "Delegations", "My tasks"]),
    );
  });
});
