/**
 * A breach's trail in words (2026-11-12): every event the breach module
 * records reads as a sentence built from what its row carries, and says
 * nothing the row does not.
 */
import { describe, expect, it } from "vitest";

import { breachSentence } from "@/components/data-display/audit-breach-words";
import { eventSentence } from "@/components/data-display/audit-detail";
import { formatDate } from "@/lib/format";
import type { AuditEntry } from "@/types";

const entry = (event_type: string, detail: Record<string, unknown> = {}): AuditEntry =>
  ({
    log_uuid: "l1",
    event_type,
    entity_type: event_type.startsWith("breach_ticket") ? "breach_ticket" : "breach",
    entity_id: 7,
    occurred_at: "2026-11-12T10:00:00Z",
    detail: { reference: "BR-2026-0200", ...detail },
  }) as unknown as AuditEntry;

const said = (event_type: string, detail?: Record<string, unknown>) => eventSentence(entry(event_type, detail));

/** Every event the server declares for the module (`domain/audit/service.py`). */
const EVENTS = [
  "breach.recorded",
  "breach.confirmed",
  "breach.determined",
  "breach.assessed",
  "breach.cert_in_marked",
  "breach.cert_in_set_aside",
  "breach.obligation_created",
  "breach.obligation_completed",
  "breach.obligation_not_applicable",
  "breach.obligation_reinstated",
  "breach.obligation_extended",
  "breach.closed",
  "breach.reopened",
  "breach.attachment_added",
  "breach.attachment_read",
  "breach.affected_revised",
  "breach.affected_uploaded",
  "breach.obligation_reopened",
  "breach.notice_drafted",
  "breach.notice_edited",
  "breach.notice_approved",
  "breach.notice_sent",
  "breach_notice.delivered",
  "breach_ticket.assigned",
  "breach_ticket.message",
  "breach_ticket.returned",
  "breach_ticket.sent_back",
  "breach_ticket.closed",
  "breach_ticket.withdrawn",
  "breach_ticket.reopened",
  "breach_ticket.date_changed",
  "breach_ticket.file_read",
  "breach_ticket.colleague_added",
  "incident_report.received",
  "incident_report.claimed",
  "incident_report.dismissed",
  "incident_report.reporter_erased",
  "breach.report_drafted",
  "breach.report_edited",
  "breach.report_finalised",
  "breach.report_resent",
  "breach.report_delivered",
  "breach.report_failed",
  "breach.report_proof_added",
  "breach.report_filed",
  "breach.report_read",
  "breach.report_released",
  "breach.report_withheld",
  "breach_settings.changed",
];

describe("a breach's trail, in words", () => {
  it("has a sentence for every event of the module, with or without its detail", () => {
    for (const event of EVENTS) {
      for (const detail of [{}, { kind: "org_board", version: 2, duty: "cert_in", reason_given: true }]) {
        const sentence = breachSentence(entry(event, detail));
        expect(sentence, event).toBeTruthy();
        // A sentence: capital, full stop, and nothing left half-made.
        expect(sentence, event).toMatch(/^[A-Z].*\.$/);
        expect(sentence, event).not.toMatch(/undefined|null|NaN|\[object|,\.|\s\s/);
      }
    }
    // And is silent about anything else.
    expect(breachSentence(entry("project.created"))).toBeNull();
  });

  it("says who a report went to and what became of each mail", () => {
    expect(said("breach.report_finalised", { kind: "org_board", version: 1, mailed: 3, added: 1, held: false })).toBe(
      "The report to the organisation's board, version 1, was finalised and sent to 3 addresses, 1 of them added for this report alone.",
    );
    expect(said("breach.report_finalised", { kind: "cert_in", version: 1, mailed: 0, held: true })).toBe(
      "The report to CERT-In, version 1, was finalised and is held until the validation.",
    );
    expect(said("breach.report_finalised", { kind: "board_report", version: 2, mailed: 0, held: false })).toBe(
      "The detailed report to the Data Protection Board, version 2, was finalised.",
    );
    expect(said("breach.report_delivered", { kind: "org_board", version: 1, recipient: "r1" })).toBe(
      "The report to the organisation's board, version 1, reached one of its addresses.",
    );
    expect(said("breach.report_failed", { kind: "org_board", version: 1, error: "SMTPDataError" })).toBe(
      "The report to the organisation's board, version 1, could not be delivered to one of its addresses (SMTPDataError).",
    );
    expect(said("breach.report_filed", { kind: "board_intimation", version: 1 })).toBe(
      "The first intimation to the Data Protection Board, version 1, was recorded as sent to the regulator.",
    );
    expect(said("breach.report_proof_added", { kind: "cert_in", version: 1, proof: "sent_mail" })).toBe(
      "Proof was added to the report to CERT-In, version 1: the mail as it was sent.",
    );
  });

  it("names the duty, when it is due and how it came to be done", () => {
    expect(said("breach.obligation_created", { duty: "principals", due_at: null })).toBe(
      "A duty started: the notice to the people affected; due without delay.",
    );
    expect(
      said("breach.obligation_completed", { duty: "org_board", late: true, reached: 2, by: "delivery", version: 1 }),
    ).toBe(
      "A duty was completed, after its due time: the report to the organisation's board. Its mail reached 2 addresses.",
    );
    expect(said("breach.obligation_completed", { duty: "board_intimation", late: false, by: "filing" })).toBe(
      "A duty was completed: the first intimation to the Data Protection Board. It was recorded as sent to the regulator.",
    );
    expect(said("breach.determined", { outcome: "no", reason_given: true })).toBe(
      "Validated: this is not a personal data breach, with a reason.",
    );
  });

  it("says what happened on a ticket, and never a reason's words", () => {
    expect(said("breach_ticket.assigned", { ticket: "t1", answer_by: "2026-11-20" })).toBe(
      `A ticket was assigned, to be resolved by ${formatDate("2026-11-20")}.`,
    );
    expect(said("breach_ticket.assigned", { ticket: "t1", answer_by: null })).toBe("A ticket was assigned.");
    expect(
      said("breach_ticket.date_changed", {
        ticket: "t1",
        side: "holder",
        date_before: "2026-11-20",
        date_after: "2026-11-27",
        reason_given: true,
      }),
    ).toBe(
      `The holder changed the ticket's resolve-by date from ${formatDate("2026-11-20")} to ${formatDate("2026-11-27")}, with a reason.`,
    );
    expect(said("breach_ticket.returned", { ticket: "t1", outcome: "partial", file: true })).toBe(
      "The holder answered the ticket: did part of it, with a file.",
    );
    expect(said("breach_ticket.withdrawn", { ticket: "t1", reason_given: true })).toBe(
      "The office withdrew the ticket, with a reason.",
    );
  });

  it("counts the people affected as the row counts them", () => {
    expect(
      said("breach.affected_revised", { revision: 2, derived: 1818, excluded: 3, added_by_hand: 0, newly_listed: 12 }),
    ).toBe(
      "The list of people affected was confirmed, revision 2: 1818 found from the records, 3 excluded, 12 newly listed.",
    );
    expect(said("breach.notice_sent", { version: 1, accounts: 40, queued: 1, retried: 0 })).toBe(
      "The notice to the people affected, version 1, was sent: 40 accounts told on the portal, 1 message queued by email or SMS.",
    );
  });
});
