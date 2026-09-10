/**
 * One rights request, the way the flow diagram draws it.
 *
 * Three columns on the diagram - the clock, the path, where it can end early -
 * and the same three here, followed by the cards that do the work in the
 * order the path asks the questions: identity, classification, holders, the
 * erasure scope, the transitions the server offers, and the response. Nothing
 * on this page decides what may happen next; every card renders the server's
 * answer and shows its sentence when it refuses.
 */
"use client";

import { ArrowLeft, Download, History } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { ActivityFeed } from "@/components/data-display/activity-feed";
import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import { ClockColumn } from "@/features/rights/components/clock-column";
import { REQUEST_TYPE_COPY, RequestStatusBadge, RequestTypeBadge } from "@/features/rights/components/copy";
import { HoldersCard } from "@/features/rights/components/holders-card";
import { LinkedFrom, LinkedRequestCard } from "@/features/rights/components/linked-request-card";
import { Path } from "@/features/rights/components/path";
import { RespondCard } from "@/features/rights/components/respond-card";
import { ScopeCard } from "@/features/rights/components/scope-card";
import { ClassificationCard, RequestTransitions, VerificationCard } from "@/features/rights/components/staff-actions";
import { useRequest, useRequestTrail } from "@/features/rights/queries";
import { config } from "@/lib/config";
import { formatDateTime, humanise } from "@/lib/format";

export default function RequestDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params?.uuid;
  const request = useRequest(uuid);
  const [trailOpen, setTrailOpen] = React.useState(false);
  const trail = useRequestTrail(trailOpen ? uuid : undefined);

  if (request.isLoading) return <Skeleton className="h-96" />;
  if (request.error) {
    return (
      <Alert tone="danger" title="Could not load this request">
        {request.error.userMessage()}
      </Alert>
    );
  }
  const r = request.data;
  if (!r) return null;

  const closed = r.status === "closed";
  const withHolders = r.request_type !== "grievance";

  return (
    <>
      <PageHeader
        eyebrow="Rights request"
        breadcrumb={
          <Link href="/requests" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Rights requests
          </Link>
        }
        title={r.reference}
        description={`${REQUEST_TYPE_COPY[r.request_type].label} · ${REQUEST_TYPE_COPY[r.request_type].section} · ${humanise(r.channel)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <RequestTypeBadge type={r.request_type} />
            <RequestStatusBadge status={r.status} outcome={r.outcome} />
          </div>
        }
      />

      <div className="space-y-6">
        <Card>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="Who">
                {r.subject_uuid ? (
                  <>
                    <Link href={`/users`} className="text-accent-text hover:underline">{r.subject_name}</Link>
                    <span className="block text-xs text-text-subtle">{r.subject_email}{r.subject_mobile && ` · ${r.subject_mobile}`}</span>
                  </>
                ) : (
                  <>
                    <span>{r.submitted_name ?? "No name given"}</span>
                    <span className="block text-xs text-warning-text">No account matches this contact</span>
                  </>
                )}
              </DescriptionItem>
              <DescriptionItem term="Contact given">{r.submitted_contact}</DescriptionItem>
              <DescriptionItem term="Received">{formatDateTime(r.received_at)}</DescriptionItem>
              <DescriptionItem term="Acknowledged">{r.acknowledged_at ? formatDateTime(r.acknowledged_at) : "Not yet"}</DescriptionItem>
              {r.linked_reference && (
                <DescriptionItem term="About">
                  <Mono>{r.linked_reference}</Mono>
                  <span className="ml-2 text-xs text-text-subtle">
                    {r.request_type === "grievance" ? "the request under dispute, shown below" : "shown below"}
                  </span>
                </DescriptionItem>
              )}
              <LinkedFrom request={r} />
              {r.channel === "nominee" && (
                <DescriptionItem term="Nominee">
                  {r.nominee_name} ({r.nominee_contact}) · {r.trigger_event === "death" ? "reports the principal has died" : "reports the principal cannot act"}
                  {r.trigger_evidence_hash && (
                    <a className="ml-2 inline-flex items-center gap-1 text-accent-text underline underline-offset-2" href={`${config.apiUrl}/requests/${r.request_uuid}/event/evidence`}>
                      <Download className="size-3.5" aria-hidden="true" /> evidence
                    </a>
                  )}
                </DescriptionItem>
              )}
              {r.about_dpo && (
                <DescriptionItem term="Reviewer">{r.reviewer_name ?? "Not yet assigned - an administrator names one"}</DescriptionItem>
              )}
            </DescriptionList>
            <p className="mt-4 whitespace-pre-wrap rounded-md bg-bg-inset p-3 text-sm">{r.request_text}</p>
          </CardBody>
        </Card>

        <LinkedRequestCard request={r} />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
          <Card>
            <CardHeader>
              <CardTitle>Clock</CardTitle>
            </CardHeader>
            <CardBody>
              <ClockColumn clock={r.clock} closed={closed} />
            </CardBody>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>The path, and where it can end early</CardTitle>
            </CardHeader>
            <CardBody>
              <Path request={r} />
            </CardBody>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <VerificationCard request={r} />
          <ClassificationCard request={r} />
        </div>

        {withHolders && <HoldersCard request={r} />}
        {r.request_type === "erasure" && <ScopeCard request={r} />}

        <div className="grid gap-6 lg:grid-cols-2">
          <RequestTransitions request={r} />
          <RespondCard request={r} />
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <History className="size-4" aria-hidden="true" />
              What was recorded
            </CardTitle>
            <button type="button" className="text-sm text-accent-text underline underline-offset-2" onClick={() => setTrailOpen((v) => !v)} aria-expanded={trailOpen}>
              {trailOpen ? "Hide" : "Show"}
            </button>
          </CardHeader>
          {trailOpen && (
            <CardBody>
              <ActivityFeed entries={trail.data} isLoading={trail.isLoading} order="oldest" emptyTitle="Nothing recorded yet" />
            </CardBody>
          )}
        </Card>
      </div>
    </>
  );
}
