/**
 * The request a grievance is about, on the grievance.
 *
 * A grievance is decided by asking one question of the original: was the
 * handling wrong, incomplete, or late? Answering it means reading what she
 * asked, what came back, when, and whether every holder returned its ticket -
 * so all of that sits here, on the page where the decision is made, instead
 * of behind a reference the reviewer has to go and find. The full record is a
 * link away when the reader's scope reaches it; when it does not (a reviewer
 * named because the complaint is about the DPO), this summary and the trail
 * are what the grievance carries, and the card says so.
 *
 * The same card serves a re-run: there the linked request is the grievance
 * that ordered it, and the question is what the grievance found.
 */
"use client";

import { ArrowUpRight, History } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { ActivityFeed } from "@/components/data-display/activity-feed";
import {
  Badge,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Mono,
} from "@/components/ui/primitives";
import { OUTCOME_COPY, RequestStatusBadge, RequestTypeBadge } from "@/features/rights/components/copy";
import { useLinkedTrail } from "@/features/rights/queries";
import { formatDate, formatDateTime, humanise, shortHash } from "@/lib/format";
import type { LinkedRef, LinkedRequest, RightsRequestDetail } from "@/types";

const DAY = 24 * 60 * 60 * 1000;

/** Whole days between the deadline and the answer, positive when late. Pure:
 * both dates come from the server, so the answer does not move with the clock. */
export function daysLate(dueAt: string, respondedAt: string | null): number | null {
  if (!respondedAt) return null;
  const late = Math.floor((new Date(respondedAt).getTime() - new Date(dueAt).getTime()) / DAY);
  return late > 0 ? late : 0;
}

/** How the original was answered, in one phrase: on time, or how late. */
export function timelinessCopy(linked: LinkedRequest): { text: string; late: boolean } {
  const late = daysLate(linked.due_at, linked.responded_at);
  if (late === null) {
    return linked.clock.overdue
      ? { text: `Still open, ${linked.clock.days_remaining * -1} days past its date`, late: true }
      : { text: `Still open, ${linked.clock.days_remaining} days left`, late: false };
  }
  if (late === 0) return { text: "Answered within the period", late: false };
  return { text: `Answered ${late} ${late === 1 ? "day" : "days"} after its date`, late: true };
}

function titleFor(request: RightsRequestDetail, linked: LinkedRequest): string {
  if (request.request_type === "grievance") return "The request under dispute";
  if (linked.request_type === "grievance") return "The grievance that ordered this re-run";
  return "The request this is linked to";
}

export function LinkedRequestCard({ request: r }: { request: RightsRequestDetail }) {
  const linked = r.linked_request;
  const [trailOpen, setTrailOpen] = React.useState(false);
  const trail = useLinkedTrail(trailOpen ? r.request_uuid : undefined);
  if (!linked) return null;

  const timeliness = timelinessCopy(linked);
  const unreturned = linked.tickets_issued - linked.tickets_returned;
  const returned = linked.response_text ?? linked.refusal_reason;

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="flex flex-wrap items-center gap-2">
            {titleFor(r, linked)}
            <Mono>{linked.reference}</Mono>
          </CardTitle>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
            <RequestTypeBadge type={linked.request_type} />
            <RequestStatusBadge status={linked.status} outcome={linked.outcome} />
            <span>{humanise(linked.channel)}</span>
          </p>
        </div>
        {linked.in_scope ? (
          <Link href={`/requests/${linked.request_uuid}`} className="inline-flex items-center gap-1 text-sm text-accent-text underline underline-offset-2">
            Open {linked.reference} in full
            <ArrowUpRight className="size-3.5" aria-hidden="true" />
          </Link>
        ) : (
          <span className="max-w-xs text-xs text-text-subtle">
            The full record is outside your scope. What is here, and its trail below, is what the grievance carries.
          </span>
        )}
      </CardHeader>
      <CardBody className="space-y-4">
        <DescriptionList>
          <DescriptionItem term="Asked">{formatDateTime(linked.received_at)}</DescriptionItem>
          <DescriptionItem term="Due">{formatDate(linked.due_at)}</DescriptionItem>
          <DescriptionItem term="Answered">
            {linked.responded_at ? formatDateTime(linked.responded_at) : "Not yet"}
            <Badge tone={timeliness.late ? "danger" : "success"} dot={false} className="ml-2">
              {timeliness.text}
            </Badge>
          </DescriptionItem>
          <DescriptionItem term="Identity">
            {linked.verification_method
              ? `${humanise(linked.verification_method)}${linked.verified_at ? ` · ${formatDateTime(linked.verified_at)}` : ""}`
              : "Never verified"}
          </DescriptionItem>
          {linked.request_type !== "grievance" && (
            <DescriptionItem term="Holders">
              {linked.holder_count === 0
                ? "None named"
                : `${linked.tickets_issued} of ${linked.holder_count} asked · ${linked.tickets_returned} returned`}
              {unreturned > 0 && (
                <Badge tone="warning" dot={false} className="ml-2">
                  {unreturned} never returned
                </Badge>
              )}
            </DescriptionItem>
          )}
          {linked.response_file_hash && (
            <DescriptionItem term="File released">sha256 {shortHash(linked.response_file_hash, 12)}</DescriptionItem>
          )}
        </DescriptionList>

        <div>
          <p className="text-2xs font-semibold uppercase tracking-wide text-text-subtle">What was asked</p>
          <p className="mt-1 whitespace-pre-wrap rounded-md bg-bg-inset p-3 text-sm">{linked.request_text}</p>
        </div>

        <div>
          <p className="text-2xs font-semibold uppercase tracking-wide text-text-subtle">
            What was returned{linked.outcome && ` · ${OUTCOME_COPY[linked.outcome].label}`}
          </p>
          {returned ? (
            <p className="mt-1 whitespace-pre-wrap rounded-md bg-bg-inset p-3 text-sm">{returned}</p>
          ) : (
            <p className="mt-1 text-sm text-text-muted">Nothing has been returned yet.</p>
          )}
          {linked.remedy_text && (
            <p className="mt-2 text-sm">
              <span className="font-medium">Remedy: </span>
              {linked.remedy_text}
            </p>
          )}
        </div>

        <div>
          <button
            type="button"
            className="inline-flex items-center gap-1 text-sm text-accent-text underline underline-offset-2"
            onClick={() => setTrailOpen((v) => !v)}
            aria-expanded={trailOpen}
          >
            <History className="size-4" aria-hidden="true" />
            {trailOpen ? "Hide" : "Show"} what was recorded on {linked.reference}
          </button>
          {trailOpen && (
            <div className="mt-3">
              <ActivityFeed entries={trail.data} isLoading={trail.isLoading} order="oldest" emptyTitle="Nothing recorded" />
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

function followerCopy(ref: LinkedRef): string {
  if (ref.request_type === "grievance") return "Disputed by";
  return "Re-run as";
}

/** The requests that followed this one, named on it: the grievance that
 * disputes it, or the re-run a grievance ordered. Nothing when there are none. */
export function LinkedFrom({ request: r }: { request: RightsRequestDetail }) {
  if (r.linked_from.length === 0) return null;
  return (
    <DescriptionItem term="Followed by">
      <ul className="space-y-1">
        {r.linked_from.map((f) => (
          <li key={f.request_uuid} className="flex flex-wrap items-center gap-2">
            <span>{followerCopy(f)}</span>
            <Link href={`/requests/${f.request_uuid}`} className="text-accent-text hover:underline">
              <Mono>{f.reference}</Mono>
            </Link>
            <RequestStatusBadge status={f.status} outcome={f.outcome} />
            <span className="text-xs text-text-subtle">{formatDate(f.received_at)}</span>
          </li>
        ))}
      </ul>
    </DescriptionItem>
  );
}
