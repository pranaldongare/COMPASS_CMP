/**
 * What the manual says a yes after a no completes (review 2026-11-08,
 * duties-4 and portal-docs-6). It completes the duty to tell the
 * organisation's board and the DPDP Board's two reports from what was done
 * meanwhile, and never the notice to the people affected; a report to CERT-In
 * recorded as sent completes its duty at once, whatever a no says. The console
 * alone has this manual's breach pages, so this is not a shared file.
 */
import { describe, expect, it } from "vitest";

import { SECTIONS } from "@/features/help/content";
import type { HelpBlock } from "@/features/help/types";

const steps = SECTIONS.flatMap((s) => s.blocks)
  .filter((b): b is Extract<HelpBlock, { kind: "steps" }> => b.kind === "steps")
  .flatMap((b) => b.items);

const step = (start: string) => steps.find((t) => t.startsWith(start)) ?? "";

describe("the breach manual", () => {
  it("says what a yes after a no finds done, and no more", () => {
    const validation = step("Record the [[Validation]]");

    expect(validation).not.toMatch(/a duty whose work was done meanwhile/);
    expect(validation).toMatch(
      /the organisation's board's duty, from the first of its reports that reached somebody/,
    );
    expect(validation).toMatch(
      /initial intimation and the 72-hour report, from the first recorded as sent/,
    );
    expect(validation).toMatch(/The notice to the people affected is not done by the yes/);
    expect(validation).toMatch(/A no leaves the CERT-In duty as it is/);
  });

  it("limits what waits for the next yes to the DPDP Board's reports, and the first filing", () => {
    const filing = step("Then click [[Record as sent]]");
    const atTheYes = filing.split(/(?<=[.;:])\s/).filter((t) => /at the next yes/.test(t));

    expect(atTheYes.length).toBeGreaterThan(0);
    for (const sentence of atTheYes)
      expect(sentence).toMatch(/initial intimation or 72-hour report/);
    expect(filing).toMatch(/the first recorded is the one that counts/);
    expect(filing).toMatch(
      /A report to CERT-In recorded as sent completes its duty at once/,
    );
  });
});
