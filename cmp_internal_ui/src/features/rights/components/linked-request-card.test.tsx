/**
 * The one question a grievance asks of the original - was it late? - answered
 * from the server's dates alone, so the answer does not drift with the clock.
 */
import { describe, expect, it } from "vitest";

import { daysLate, timelinessCopy } from "@/features/rights/components/linked-request-card";
import { makeClock } from "@/test/fixtures";
import type { LinkedRequest } from "@/types";

function linked(overrides: Partial<LinkedRequest> = {}): LinkedRequest {
  return {
    request_uuid: "11111111-1111-4111-8111-111111111111",
    reference: "RR-2026-000001",
    request_type: "access",
    status: "closed",
    outcome: "complete",
    received_at: "2026-08-01T10:00:00Z",
    closed_at: "2026-08-20T10:00:00Z",
    channel: "portal",
    request_text: "What do you hold?",
    due_at: "2026-08-31T00:00:00Z",
    verification_method: "session",
    verified_at: "2026-08-01T10:00:00Z",
    responded_at: "2026-08-20T10:00:00Z",
    response_text: "Here it is.",
    refusal_reason: null,
    remedy_text: null,
    response_file_hash: null,
    holder_count: 1,
    tickets_issued: 1,
    tickets_returned: 1,
    clock: makeClock(),
    in_scope: true,
    ...overrides,
  };
}

describe("daysLate", () => {
  it("is zero when the answer came within the period", () => {
    expect(daysLate("2026-08-31T00:00:00Z", "2026-08-20T10:00:00Z")).toBe(0);
  });
  it("counts whole days past the date", () => {
    expect(daysLate("2026-08-31T00:00:00Z", "2026-09-03T12:00:00Z")).toBe(3);
  });
  it("is unknown while there is no answer", () => {
    expect(daysLate("2026-08-31T00:00:00Z", null)).toBeNull();
  });
});

describe("timelinessCopy", () => {
  it("says on time", () => {
    expect(timelinessCopy(linked())).toEqual({ text: "Answered within the period", late: false });
  });
  it("says how late, in days", () => {
    const copy = timelinessCopy(linked({ responded_at: "2026-09-01T09:00:00Z" }));
    expect(copy).toEqual({ text: "Answered 1 day after its date", late: true });
  });
  it("reads the clock while the original is still open", () => {
    const open = linked({ status: "in_progress", outcome: null, responded_at: null, clock: makeClock({ overdue: true, days_remaining: -4 }) });
    expect(timelinessCopy(open)).toEqual({ text: "Still open, 4 days past its date", late: true });
  });
});
