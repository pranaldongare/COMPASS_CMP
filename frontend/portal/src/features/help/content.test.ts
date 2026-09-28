/**
 * The manual's content holds together: every anchor is unique, every role a
 * section names is a real one, and every label marker is closed - an unclosed
 * `[[` would print brackets on the page.
 */

import { describe, expect, it } from "vitest";

import * as content from "@/features/help/content";
import type { HelpBlock } from "@/features/help/types";

const roles = "ROLES" in content ? (content.ROLES as { value: string }[]) : [];

function texts(block: HelpBlock): string[] {
  switch (block.kind) {
    case "p":
      return [block.text];
    case "note":
    case "tip":
    case "warning":
      return [block.title ?? "", block.text];
    case "steps":
    case "list":
      return [block.title ?? "", ...block.items];
    case "faq":
      return block.items.flatMap((i) => [i.q, i.a]);
    case "terms":
      return block.items.flatMap((i) => [i.term, i.meaning]);
  }
}

describe("help content", () => {
  it("has a unique anchor for every section", () => {
    const ids = content.SECTIONS.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(id).toMatch(/^[a-z0-9-]+$/);
  });

  it("names only roles the manual offers", () => {
    const known = new Set(roles.map((r) => r.value));
    for (const section of content.SECTIONS) {
      for (const role of section.roles ?? [])
        expect(known.has(role), `${section.id}: ${role}`).toBe(true);
    }
  });

  it("closes every label it opens", () => {
    for (const section of content.SECTIONS) {
      for (const text of section.blocks.flatMap(texts)) {
        const opened = text.split("[[").length - 1;
        const closed = text.split("]]").length - 1;
        expect(opened, `${section.id}: ${text}`).toBe(closed);
      }
    }
  });
});
