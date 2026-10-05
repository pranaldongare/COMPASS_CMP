/**
 * The consent chart says what each record actually is (UX review 2026-10-05).
 *
 * It showed "Still standing" as every current record minus the complete
 * withdrawals, which counted a person who declined everything as consent
 * still standing. The server now counts the four states apart, and the chart
 * shows them as they are.
 */
import { describe, expect, it } from "vitest";

import { consentComposition } from "@/features/dashboard/components/helpers";

describe("consentComposition", () => {
  it("shows the four states the server counted, and nothing called standing", () => {
    const view = consentComposition({
      total_consents: 10,
      withdrawals: 2,
      consents_full: 4,
      consents_partial: 3,
      consents_declined: 1,
      consents_withdrawn: 2,
    });
    expect(view?.segments.map((s) => [s.label, s.value])).toEqual([
      ["Agreed to all purposes", 4],
      ["Agreed to some", 3],
      ["Declined", 1],
      ["Withdrawn", 2],
    ]);
    expect(view?.segments.some((s) => /standing/i.test(s.label))).toBe(false);
    // Each number is shown once: the chart has explained these.
    expect(view?.consumed).toEqual(
      expect.arrayContaining(["total_consents", "withdrawals", "consents_full"]),
    );
  });

  it("draws nothing rather than guess when the states are not there", () => {
    expect(consentComposition({ total_consents: 10, withdrawals: 2 })).toBeNull();
  });
});
