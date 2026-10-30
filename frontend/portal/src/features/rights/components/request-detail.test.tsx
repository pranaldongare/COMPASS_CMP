/**
 * Where a request stands, in her words (2026-10-30): four steps - received,
 * confirmed it was her, gathering her data, the answer - instead of the
 * office's clock checkpoints and flow diagram.
 */
import { describe, expect, it } from "vitest";

import { progressSteps } from "@/features/rights/components/request-detail";
import { makeClock, makeMyRequest } from "@/test/fixtures";

function states(...args: Parameters<typeof makeMyRequest>) {
  return progressSteps(makeMyRequest(...args)).map((s) => `${s.label}: ${s.state}`);
}

describe("progressSteps", () => {
  it("waits for her to confirm it was her", () => {
    expect(states({ verification_status: "pending" })).toEqual([
      "Received: done",
      "Confirm it was you: current",
      "We gather your data: todo",
      "Your answer: todo",
    ]);
  });

  it("says the data is being gathered once the office is at work", () => {
    const steps = progressSteps(makeMyRequest({ status: "awaiting_holders" }));
    expect(steps[2]).toMatchObject({
      label: "We are gathering your data",
      note: "from the teams that hold it",
      state: "current",
    });
  });

  it("is all done once answered", () => {
    expect(
      states({
        status: "closed",
        outcome: "complete",
        responded_at: "2026-10-30T11:00:00Z",
        closed_at: "2026-10-30T11:00:00Z",
      }),
    ).toEqual([
      "Received: done",
      "We confirmed it was you: done",
      "We gathered your data: done",
      "Answered: done",
    ]);
  });

  it("skips what never happened when a request ends early", () => {
    expect(
      states({
        status: "closed",
        outcome: "not_verified",
        verification_status: "failed",
        closed_at: "2026-10-30T11:00:00Z",
      }),
    ).toEqual([
      "Received: done",
      "We could not confirm it was you: skipped",
      "Data gathered: skipped",
      "Answered: done",
    ]);
  });

  it("says when an answer is late", () => {
    const steps = progressSteps(
      makeMyRequest({ status: "in_progress", clock: makeClock({ overdue: true }) }),
    );
    expect(steps[3]).toMatchObject({ late: true });
    expect(steps[3].note).toMatch(/^was due /);
  });
});
