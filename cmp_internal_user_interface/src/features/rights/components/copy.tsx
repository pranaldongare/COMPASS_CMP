/**
 * The words the rights screens share, and the badges that go with them.
 *
 * One place, because the same right is named on the public form, the data
 * principal's page, the DPO's register and the acknowledgement she receives,
 * and four spellings of "erasure" is how somebody ends up unsure whether they
 * asked for the right thing.
 */
"use client";

import { Badge } from "@/components/ui/primitives";
import type {
  RightsRequestOutcome,
  RightsRequestStatus,
  RightsRequestType,
  RightsTicketStatus,
} from "@/types";

export const REQUEST_TYPE_COPY: Record<
  RightsRequestType,
  { label: string; section: string; blurb: string }
> = {
  access: {
    label: "Access",
    section: "s.11",
    blurb:
      "A summary of the personal data we hold about you, what we do with it, and who it has been shared with.",
  },
  correction: {
    label: "Correction",
    section: "s.12",
    blurb: "Correct inaccurate personal data, or complete data that is incomplete.",
  },
  erasure: {
    label: "Erasure",
    section: "s.12(3)",
    blurb:
      "Erase personal data that is no longer needed. Consent records are kept as evidence of what was agreed; withdrawing consent is a separate, quicker step you can take yourself.",
  },
  grievance: {
    label: "Grievance",
    section: "s.13",
    blurb:
      "Complain about how a request, or your data, was handled - late, incomplete, or wrong. Disagreement with an outcome counts.",
  },
};

export const STATUS_COPY: Record<RightsRequestStatus, { label: string; tone: BadgeTone }> = {
  received: { label: "Received", tone: "warning" },
  in_progress: { label: "In progress", tone: "info" },
  awaiting_holders: { label: "Awaiting holders", tone: "warning" },
  collating: { label: "Collating", tone: "info" },
  closed: { label: "Closed", tone: "neutral" },
};

export const OUTCOME_COPY: Record<RightsRequestOutcome, { label: string; tone: BadgeTone }> = {
  complete: { label: "Complete", tone: "success" },
  partial: { label: "Partial", tone: "warning" },
  no_records: { label: "No records held", tone: "success" },
  refused: { label: "Refused", tone: "danger" },
  not_verified: { label: "Not verified", tone: "danger" },
  reclassified_withdrawal: { label: "Handled as withdrawal", tone: "neutral" },
  upheld: { label: "Upheld", tone: "success" },
  not_upheld: { label: "Not upheld", tone: "neutral" },
};

export const TICKET_COPY: Record<RightsTicketStatus, { label: string; tone: BadgeTone }> = {
  pending: { label: "No ticket yet", tone: "neutral" },
  issued: { label: "Issued", tone: "info" },
  escalated: { label: "Escalated", tone: "warning" },
  returned: { label: "Returned", tone: "success" },
  unreturned: { label: "Never returned", tone: "danger" },
};

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

export function RequestTypeBadge({ type }: { type: RightsRequestType }) {
  const copy = REQUEST_TYPE_COPY[type];
  return (
    <Badge tone="neutral" dot={false}>
      {copy.label} · {copy.section}
    </Badge>
  );
}

export function RequestStatusBadge({
  status,
  outcome,
}: {
  status: RightsRequestStatus;
  outcome: RightsRequestOutcome | null;
}) {
  // A closed request reads as its outcome, not as "closed": the outcome is the
  // answer she was given, and "closed" says nothing about it.
  if (status === "closed" && outcome) {
    const copy = OUTCOME_COPY[outcome];
    return <Badge tone={copy.tone}>{copy.label}</Badge>;
  }
  const copy = STATUS_COPY[status];
  return <Badge tone={copy.tone}>{copy.label}</Badge>;
}

export function TicketBadge({ status }: { status: RightsTicketStatus }) {
  const copy = TICKET_COPY[status];
  return (
    <Badge tone={copy.tone} dot={false}>
      {copy.label}
    </Badge>
  );
}
