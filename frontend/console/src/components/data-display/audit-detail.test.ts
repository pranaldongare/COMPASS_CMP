/**
 * What the trail says of a ticket's date being moved (2026-11-12).
 *
 * The trail marks that a reason was given and keeps none of its words (ADR
 * 0015). The words come beside the entry, from the ticket's own message, so
 * the sentence still answers who gave a holder longer and on what ground:
 * both dates, which side moved it and why - and only the change, to a reader
 * who may not open the reason or once the message is gone.
 */
import { describe, expect, it } from "vitest";

import { eventSentence } from "@/components/data-display/audit-detail";
import { formatDate } from "@/lib/format";
import type { AuditEntry } from "@/types";

const entry = (detail: Record<string, unknown>, reason?: string | null): AuditEntry =>
  ({
    log_uuid: "l1",
    event_type: "rights.ticket_date_changed",
    entity_type: "rights_request_holder",
    entity_id: 7,
    occurred_at: "2026-11-12T10:00:00Z",
    detail,
    reason,
  }) as unknown as AuditEntry;

const moved = {
  side: "office",
  date_before: "2026-11-20T18:29:00Z",
  date_after: "2026-11-27T18:29:00Z",
  reason_given: true,
  message_uuid: "m1",
};

describe("the trail's sentence for a date change", () => {
  it("names the two dates, the side and the reason read from the ticket's message", () => {
    const said = eventSentence(
      entry(
        moved,
        "Answer by changed from 20 November 2026 to 27 November 2026: Their archive is offline until Friday",
      ),
    );
    expect(said).toBe(
      `The office changed a ticket's answer-by date from ${formatDate("2026-11-20T18:29:00Z")} to ${formatDate("2026-11-27T18:29:00Z")}. Reason: Their archive is offline until Friday`,
    );
  });

  it("keeps a colon the reason has of its own", () => {
    const said = eventSentence(
      entry(moved, "Answer by changed from 20 November 2026 to 27 November 2026: Audit: until Friday"),
    );
    expect(said).toContain("Reason: Audit: until Friday");
  });

  it("says the holder moved it when they did, and no date where there was none", () => {
    const said = eventSentence(
      entry(
        { ...moved, side: "holder", date_before: null },
        "Answer by changed from no date to 27 November 2026: On leave",
      ),
    );
    expect(said).toContain("The holder changed a ticket's answer-by date from no date to");
    expect(said).toContain("Reason: On leave");
  });

  it("leaves a reason the reader cannot open unsaid", () => {
    const said = eventSentence(entry(moved, "SE::RElBQUFB"));
    expect(said).not.toContain("SE::");
    expect(said).not.toContain("Reason:");
  });

  it("says a reason was given once the ticket's message is gone", () => {
    const said = eventSentence(entry(moved, null));
    expect(said).toContain("A reason was given; it is no longer on the ticket.");
  });
});
