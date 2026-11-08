/**
 * What the manual promises somebody whose report from the public link was not
 * taken up (review 2026-11-08). A rights request from the same address finds
 * it, but an address on the person's own account counts only once a code to it
 * has come back, so the manual says how to make it count. The portal alone has
 * this page of the manual, so this is not a shared file.
 */
import { describe, expect, it } from "vitest";

import { SECTIONS } from "@/features/help/content";

describe("the manual's page on reporting an incident", () => {
  it("says an address on the person's account must be confirmed before a request finds the report", () => {
    const page = SECTIONS.find((s) => s.id === "reporting-an-incident");
    const next = page?.blocks.find(
      (b) => b.kind === "note" && b.title === "What happens next",
    );
    const text = next && "text" in next ? next.text : "";

    expect(text).toMatch(/you can ask us through your rights, from the same email address/);
    expect(text).toMatch(
      /If that address is also on your account with us, sign in with it once, or confirm it under \[\[My profile\]\], first\./,
    );
  });
});
