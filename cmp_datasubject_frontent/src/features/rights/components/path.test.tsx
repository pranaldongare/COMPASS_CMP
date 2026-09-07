/**
 * The path reads its states off the request, never off its own reasoning.
 *
 * Each case is one row of a flow diagram: the step that should be current,
 * the early exit that should read as taken, and the steps that stay ahead.
 */

import { describe, expect, it } from "vitest";

import { stepsFor } from "@/features/rights/components/path";
import { makeMyRequest, makeRequestDetail } from "@/test/fixtures";

describe("stepsFor", () => {
  it("starts a fresh, verified access request at 'a valid access request?'", () => {
    const steps = stepsFor(makeRequestDetail({ status: "received", verification_status: "verified", classified_at: null }));
    const current = steps.find((s) => s.state === "current");
    expect(current?.title).toBe("A valid access request?");
    expect(steps[0].state).toBe("done");
    expect(steps[2].state).toBe("done"); // identity verified
  });

  it("reads a failed verification as the early exit, taken", () => {
    const steps = stepsFor(
      makeRequestDetail({ status: "closed", outcome: "not_verified", verification_status: "failed" }),
    );
    const identity = steps.find((s) => s.title === "Identity verified?");
    expect(identity?.state).toBe("exited");
    expect(identity?.exit?.taken).toBe(true);
    expect(steps.filter((s) => s.state === "current")).toHaveLength(0);
  });

  it("marks 'she meant withdrawal' when an erasure closed that way", () => {
    const steps = stepsFor(
      makeRequestDetail({
        request_type: "erasure",
        status: "closed",
        outcome: "reclassified_withdrawal",
        classified_at: "2026-09-02T10:00:00Z",
      }),
    );
    const step = steps.find((s) => s.title === "Withdrawal, or erasure?");
    expect(step?.state).toBe("exited");
    expect(step?.exit?.taken).toBe(true);
  });

  it("shows the holder gap when a response went out partial", () => {
    const steps = stepsFor(makeRequestDetail({ status: "closed", outcome: "partial", responded_at: "2026-09-03T10:00:00Z", tickets_issued: 2, tickets_outstanding: 0 }));
    const returned = steps.find((s) => s.title === "All responses returned?");
    expect(returned?.exit?.taken).toBe(true);
    expect(steps.at(-1)?.state).toBe("done");
  });

  it("prefixes a nominee's request with the event gate", () => {
    const steps = stepsFor(makeRequestDetail({ channel: "nominee", trigger_evidenced_at: null, status: "received", verification_status: "verified" }));
    expect(steps.map((s) => s.title)).toContain("Is the triggering event evidenced?");
    expect(steps.find((s) => s.state === "current")?.title).toBe("Is the triggering event evidenced?");
  });

  it("renders the principal's view from her own, thinner shape", () => {
    const steps = stepsFor(makeMyRequest({ status: "in_progress" }));
    expect(steps.find((s) => s.state === "current")?.title).toBe("Holders derived, DPO confirms");
  });

  it("escalates a grievance about the DPO on the diagram", () => {
    const steps = stepsFor(makeRequestDetail({ request_type: "grievance", about_dpo: true, status: "in_progress", classified_at: "2026-09-02T10:00:00Z" }));
    const about = steps.find((s) => s.title === "Is the complaint about the DPO?");
    expect(about?.exit?.taken).toBe(true);
  });
});
