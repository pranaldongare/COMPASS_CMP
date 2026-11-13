/**
 * What the trail says of an incident or a breach, in words (2026-11-12).
 *
 * A breach's trail read as a list of event names - "Breach obligation
 * created", "Breach report finalised" - with what happened left in the
 * detail behind each row. Every event the breach module records has a
 * sentence here, built from what the row itself carries: which duty, which
 * report and version, how many addresses, what the holder said they did.
 *
 * Only what the row holds. A reason is on the trail as "given" (ADR 0015),
 * so a sentence says "with a reason" and never invents one; a count that is
 * not there is left out rather than read as zero.
 */
import { formatDate, formatDateTime } from "@/lib/format";
import type { AuditEntry } from "@/types";

type Detail = Record<string, unknown>;

const DUTY: Record<string, string> = {
  org_board: "the report to the organisation's board",
  cert_in: "the report to CERT-In",
  board_intimation: "the first intimation to the Data Protection Board",
  board_report: "the detailed report to the Data Protection Board",
  principals: "the notice to the people affected",
};

const REPORT: Record<string, string> = {
  org_board: "The report to the organisation's board",
  cert_in: "The report to CERT-In",
  board_intimation: "The first intimation to the Data Protection Board",
  board_report: "The detailed report to the Data Protection Board",
};

const DID: Record<string, string> = {
  done: "did all of it",
  partial: "did part of it",
  failed: "could not do it",
};

const num = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;
const text = (value: unknown): string | null =>
  typeof value === "string" && value.trim() ? value : null;

/** "1 address", "3 addresses": a count with its noun. */
function count(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

function duty(d: Detail): string {
  return DUTY[String(d.duty)] ?? "a duty";
}

/** "The report to CERT-In, version 2" - or "A report" when the row does not say. */
function report(d: Detail): string {
  const name = REPORT[String(d.kind)] ?? "A report";
  const version = num(d.version);
  return version ? `${name}, version ${version},` : name;
}

function due(d: Detail): string {
  const at = text(d.due_at);
  return at ? `due ${formatDateTime(at)}` : "due without delay";
}

const withReason = (d: Detail) => (d.reason_given ? ", with a reason" : "");
const side = (d: Detail) => (d.side === "holder" ? "The holder" : "The office");
const day = (value: unknown) => (text(value) ? formatDate(String(value)) : "no date");

/** How a duty came to be complete, as the row records it (`by`). */
function completedBy(d: Detail): string {
  const reached = num(d.reached);
  const notified = num(d.notified);
  switch (d.by) {
    case "delivery":
      return reached ? ` Its mail reached ${count(reached, "address", "addresses")}.` : "";
    case "resend":
      return reached ? ` Sent again, its mail reached ${count(reached, "address", "addresses")}.` : "";
    case "filing":
      return " It was recorded as sent to the regulator.";
    case "earlier_mail":
    case "after_yes":
      return " Mail sent before the validation had already reached the board.";
    case "filed_report":
      return " A filing recorded before the validation completes it.";
    default:
      return notified ? ` ${count(notified, "person", "people")} told.` : "";
  }
}

const WORDS: Record<string, (d: Detail) => string> = {
  // ------------------------------------------------------------ the incident
  "breach.recorded": (d) =>
    d.location === "processor"
      ? "An incident was logged, at a processor."
      : d.location === "platform"
        ? "An incident was logged, on the platform itself."
        : "An incident was logged.",
  "breach.confirmed": () =>
    "The incident was recorded as a personal data breach and given its breach reference.",
  "breach.determined": (d) =>
    d.outcome === "yes"
      ? `Validated: this is a personal data breach${withReason(d)}.`
      : d.outcome === "no"
        ? `Validated: this is not a personal data breach${withReason(d)}.`
        : `The validation was recorded${withReason(d)}.`,
  "breach.assessed": (d) =>
    num(d.revision) ? `The assessment was recorded, revision ${d.revision}.` : "The assessment was recorded.",
  "breach.closed": (d) => `The breach was closed${withReason(d)}.`,
  "breach.reopened": (d) => `The breach was reopened${withReason(d)}.`,

  // ------------------------------------------------------------------ duties
  "breach.cert_in_marked": (d) => `Marked as reportable to CERT-In; ${due(d)}.`,
  "breach.cert_in_set_aside": (d) => `Reporting to CERT-In was set aside as not reportable${withReason(d)}.`,
  "breach.obligation_created": (d) => `A duty started: ${duty(d)}; ${due(d)}.`,
  "breach.obligation_completed": (d) =>
    `A duty was completed${d.late ? ", after its due time" : ""}: ${duty(d)}.${completedBy(d)}`,
  "breach.obligation_not_applicable": (d) => `A duty was set aside as not applicable: ${duty(d)}.`,
  "breach.obligation_reinstated": (d) => `A duty was reinstated: ${duty(d)}; ${due(d)}.`,
  "breach.obligation_extended": (d) =>
    `An extension from the Board was recorded for ${duty(d)}${text(d.due_at) ? `; now ${due(d)}` : ""}.`,
  "breach.obligation_reopened": (d) => `A duty was reopened: ${duty(d)}.`,

  // ----------------------------------------------------------------- reports
  "breach.report_drafted": (d) => `${report(d)} was drafted.`,
  "breach.report_edited": (d) => `${report(d)} was edited.`,
  "breach.report_finalised": (d) => {
    if (d.held) return `${report(d)} was finalised and is held until the validation.`;
    const mailed = num(d.mailed);
    if (!mailed) return `${report(d)} was finalised.`;
    const added = num(d.added);
    return (
      `${report(d)} was finalised and sent to ${count(mailed, "address", "addresses")}` +
      `${added ? `, ${added} of them added for this report alone` : ""}.`
    );
  },
  "breach.report_resent": (d) => {
    const queued = num(d.queued);
    return queued
      ? `${report(d)} was sent again to ${count(queued, "address", "addresses")}.`
      : `${report(d)} was sent again.`;
  },
  "breach.report_delivered": (d) => `${report(d)} reached one of its addresses.`,
  "breach.report_failed": (d) =>
    `${report(d)} could not be delivered to one of its addresses${text(d.error) ? ` (${d.error})` : ""}.`,
  "breach.report_proof_added": (d) =>
    `Proof was added to ${report(d).replace(/^The/, "the").replace(/^A report/, "a report").replace(/,$/, "")}: ${
      d.proof === "approval" ? "the approval to send it" : "the mail as it was sent"
    }.`,
  "breach.report_filed": (d) => `${report(d)} was recorded as sent to the regulator.`,
  "breach.report_read": (d) =>
    d.as === "email" ? `${report(d)} was opened as the email sent.` : `${report(d)} was downloaded as a PDF.`,
  "breach.report_released": (d) => {
    const queued = num(d.queued);
    return `${report(d)} held for the validation was sent${queued ? ` to ${count(queued, "address", "addresses")}` : ""}.`;
  },
  "breach.report_withheld": (d) =>
    `${report(d)} held for the validation was not sent${
      d.why === "cert_in_set_aside"
        ? ": reporting to CERT-In had been set aside"
        : d.why === "nobody_left"
          ? ": nobody it was addressed to is still on the list"
          : ""
    }.`,

  // --------------------------------------------------------- people affected
  "breach.affected_revised": (d) => {
    const parts = [
      num(d.derived) !== null ? `${d.derived} found from the records` : null,
      num(d.added_by_hand) ? `${d.added_by_hand} added by hand` : null,
      num(d.excluded) ? `${d.excluded} excluded` : null,
      num(d.newly_listed) !== null ? `${d.newly_listed} newly listed` : null,
    ].filter(Boolean);
    return `The list of people affected was confirmed${num(d.revision) ? `, revision ${d.revision}` : ""}${
      parts.length ? `: ${parts.join(", ")}` : ""
    }.`;
  },
  "breach.affected_uploaded": (d) => {
    const parts = [
      num(d.rows_read) !== null ? `${d.rows_read} read` : null,
      num(d.matched_people) ? `${d.matched_people} matched to accounts` : null,
      num(d.new_contacts) ? `${d.new_contacts} kept as contacts` : null,
      num(d.already_listed) ? `${d.already_listed} already listed` : null,
      num(d.unreadable) ? `${d.unreadable} could not be read` : null,
    ].filter(Boolean);
    return `People affected were added from a list${parts.length ? `: ${parts.join(", ")}` : ""}.`;
  },
  "breach.notice_drafted": (d) => `The notice to the people affected${version(d)} was drafted.`,
  "breach.notice_edited": (d) => `The notice to the people affected${version(d)} was edited.`,
  "breach.notice_approved": (d) => `The notice to the people affected${version(d)} was approved.`,
  "breach.notice_sent": (d) => {
    const accounts = num(d.accounts);
    const queued = num(d.queued);
    const parts = [
      accounts ? `${count(accounts, "account")} told on the portal` : null,
      queued ? `${count(queued, "message")} queued by email or SMS` : null,
    ].filter(Boolean);
    return `The notice to the people affected${version(d)} was sent${parts.length ? `: ${parts.join(", ")}` : ""}.`;
  },
  "breach_notice.delivered": (d) => `The notice${version(d)} reached this person's account.`,
  "breach.attachment_added": () => "A document was attached to the record.",
  "breach.attachment_read": () => "A document attached to the record was downloaded.",

  // ----------------------------------------------------------------- tickets
  "breach_ticket.assigned": (d) =>
    `A ticket was assigned${text(d.answer_by) ? `, to be resolved by ${day(d.answer_by)}` : ""}.`,
  "breach_ticket.message": (d) => `${side(d)} wrote on the ticket${d.file ? ", with a file" : ""}.`,
  "breach_ticket.returned": (d) =>
    `The holder answered the ticket${DID[String(d.outcome)] ? `: ${DID[String(d.outcome)]}` : ""}${
      d.file ? ", with a file" : ""
    }.`,
  "breach_ticket.sent_back": (d) => `The office sent the ticket back${withReason(d)}.`,
  "breach_ticket.closed": () => "The office closed the ticket.",
  "breach_ticket.withdrawn": (d) => `The office withdrew the ticket${withReason(d)}.`,
  "breach_ticket.reopened": (d) => `The office reopened the ticket${withReason(d)}.`,
  "breach_ticket.date_changed": (d) =>
    `${side(d)} changed the ticket's resolve-by date from ${day(d.date_before)} to ${day(d.date_after)}${withReason(d)}.`,
  "breach_ticket.file_read": () => "A file on the ticket was downloaded.",
  "breach_ticket.colleague_added": () => "The holder added a colleague, who has a ticket of their own.",

  // ------------------------------------------------- the public report, settings
  "incident_report.received": () => "An incident was reported through the public link.",
  "incident_report.claimed": () => "The report was claimed by an office and logged as an incident.",
  "incident_report.dismissed": (d) => `The report was dismissed${withReason(d)}.`,
  "incident_report.reporter_erased": () => "The reporter's name and email were erased from the report.",
  "breach_settings.changed": () =>
    "Who is told of a reported incident, or who is on the organisation's board list, was changed.",
};

function version(d: Detail): string {
  return num(d.version) ? `, version ${d.version},` : "";
}

/** The sentence for an event of the breach module, or null for any other. */
export function breachSentence(entry: AuditEntry): string | null {
  const words = WORDS[entry.event_type];
  if (!words) return null;
  // A version at the end of a sentence leaves its comma before the full stop.
  return words((entry.detail ?? {}) as Detail).replace(/,\s*\./g, ".");
}
