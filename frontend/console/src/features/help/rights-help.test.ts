/**
 * What the manual says a rights request finds of the reports a person sent
 * through the public link (review 2026-11-08). An account's email counts only
 * once a code sent to it has come back - at sign-up, at sign-in or when it was
 * confirmed - and neither the rights form's code nor one read back to an
 * officer stamps anything on the account. With no such address the card says
 * nothing was looked for. The console alone has this manual's rights pages, so
 * this is not a shared file.
 */
import { describe, expect, it } from "vitest";

import { SECTIONS } from "@/features/help/content";
import type { HelpBlock } from "@/features/help/types";

const steps = SECTIONS.flatMap((s) => s.blocks)
  .filter((b): b is Extract<HelpBlock, { kind: "steps" }> => b.kind === "steps")
  .flatMap((b) => b.items);

const step = (start: string) => steps.find((t) => t.startsWith(start)) ?? "";

describe("the rights manual", () => {
  it("says the reports from the public link are found only by an email proved to be the person's", () => {
    const reports = step("Reports from the public link: once identity is verified");

    expect(reports).not.toMatch(/dismissed, found by their email address\./);
    expect(reports).toMatch(/the address a request with no account gave/);
    expect(reports).toMatch(/an account's address once a code sent to it has come back/);
    expect(reports).toMatch(
      /A code from the rights form, or one read back to an officer, does not count\./,
    );
    expect(reports).toMatch(/With no such address the card says nothing was looked for\./);
  });
});
