/**
 * One rights request.
 *
 * Where it stands comes first: the summary card's four facts - when it is
 * due, the holders, the tickets out, what is left to decide - and beside the
 * request, the current step, who has it and the next move (UX review
 * 2026-10-05). Since 2026-10-10 (the detail look the user settled on) the
 * work sits under tabs in the order the path asks the questions: the
 * overview (the next step, the request, the clock and path), identity and
 * classification, the holders and the erasure scope, the response, and what
 * was recorded. The full clock and path, the flow diagram's three columns,
 * is folded until asked for. Nothing on this page decides what may happen
 * next; every card renders the server's answer and shows its sentence when
 * it refuses.
 */
"use client";

import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  CalendarClock,
  Clock,
  Download,
  FileText,
  History,
  Inbox,
  LayoutGrid,
  ListChecks,
  Reply,
  Scale,
  UserCheck,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { ActivityFeed } from "@/components/data-display/activity-feed";
import { AuditTrailLink } from "@/components/data-display/audit-link";
import { PageHeader } from "@/components/layout/app-shell";
import { RecordHeader, type RecordFact } from "@/components/layout/record-header";
import { CollapsibleCard } from "@/components/ui/collapsible";
import {
  Alert,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  EmptyState,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import { ClockColumn } from "@/features/rights/components/clock-column";
import { ConsentScope } from "@/features/rights/components/consent-scope";
import {
  REQUEST_TYPE_COPY,
  RequestStatusBadge,
  RequestTypeBadge,
  STATUS_COPY,
} from "@/features/rights/components/copy";
import { HoldersCard } from "@/features/rights/components/holders-card";
import {
  LinkedFrom,
  LinkedRequestCard,
} from "@/features/rights/components/linked-request-card";
import { Path, stepsFor } from "@/features/rights/components/path";
import { RequestDocuments } from "@/features/rights/components/request-documents";
import { nextMove } from "@/features/rights/components/request-summary";
import { RespondCard } from "@/features/rights/components/respond-card";
import { ScopeCard } from "@/features/rights/components/scope-card";
import {
  ClassificationCard,
  RequestTransitions,
  VerificationCard,
} from "@/features/rights/components/staff-actions";
import { useRequest, useRequestTrail } from "@/features/rights/queries";
import { config } from "@/lib/config";
import { cn, formatDate, formatDateTime, humanise } from "@/lib/format";
import type { RightsRequestDetail } from "@/types";

/**
 * The request's tabs (2026-10-10). The fragment names the tab, so a tab can
 * be linked to and survives a reload. `#holders` and `#response` were cards'
 * anchors before the tabs and are tabs' names now; `#actions` - where the
 * next move points - and `#scope` open the tab that holds them. A grievance
 * has no holders, so no holders tab.
 */
const TABS = ["overview", "identity", "holders", "response", "history"] as const;
const GRIEVANCE_TABS = ["overview", "identity", "response", "history"] as const;
type RequestTab = (typeof TABS)[number];
const SECTIONS: Record<string, RequestTab> = {
  actions: "overview",
  scope: "holders",
};

const VERIFICATION_COPY: Record<RightsRequestDetail["verification_status"], string> = {
  pending: "Not yet verified",
  verified: "Verified",
  failed: "Failed",
};

export default function RequestDetailPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params?.uuid;
  const request = useRequest(uuid);
  const grievance = request.data?.request_type === "grievance";
  const [tab, setTab, hash] = useHashTab<RequestTab>(
    grievance ? GRIEVANCE_TABS : TABS,
    "overview",
    SECTIONS,
  );
  // The trail is read when its tab is opened, as the Show button did before.
  const trail = useRequestTrail(tab === "history" ? uuid : undefined);
  const loaded = Boolean(request.data);
  // A fragment naming a card, not a tab: the tab is open by now, so bring the
  // card itself into view - the browser's own jump ran before it existed.
  React.useEffect(() => {
    if (!loaded || !Object.hasOwn(SECTIONS, hash)) return;
    document.getElementById(hash)?.scrollIntoView?.({ block: "start" });
  }, [hash, loaded]);

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
  const erasure = r.request_type === "erasure";
  const hasMoves = closed || r.transitions.some((t) => t.via === "transition");
  const nextMoveIsResponse =
    (r.transitions.find((t) => t.allowed) ?? r.transitions.find((t) => t.blocked_by))
      ?.via === "respond";
  // Only when there is something to show: the response once given, a
  // grievance's decision once it is open, or the server offering to respond.
  const responds =
    closed ||
    (r.request_type === "grievance"
      ? r.status !== "received"
      : r.transitions.some((t) => t.via === "respond"));
  const typeCopy = REQUEST_TYPE_COPY[r.request_type];
  const requester = r.subject_name ?? r.submitted_name;
  const days = Math.abs(r.clock.days_remaining);
  const dayWord = days === 1 ? "day" : "days";

  // The four facts (2026-10-10): the deadline, then where the work stands.
  // A grievance asks no holders, so its middle two say what it is about and
  // who decides it; only an erasure has items to decide.
  const facts: RecordFact[] = [
    closed
      ? {
          label: "Closed",
          value: r.closed_at ? formatDate(r.closed_at) : "Closed",
          icon: CalendarClock,
          tint: 3,
        }
      : {
          label: "Due",
          value: (
            <>
              {formatDate(r.clock.due_at)} ·{" "}
              <span
                className={cn(
                  r.clock.overdue
                    ? "text-danger-text"
                    : r.clock.at_risk
                      ? "text-warning-text"
                      : "font-normal text-text-muted",
                )}
              >
                {r.clock.overdue
                  ? `overdue by ${days} ${dayWord}`
                  : `${days} ${dayWord} left`}
              </span>
            </>
          ),
          icon: CalendarClock,
          tint: 3,
        },
    ...(withHolders
      ? ([
          {
            label: "Holders",
            value: r.holder_count
              ? `${r.holders_confirmed} of ${r.holder_count} confirmed`
              : "None named yet",
            icon: Users,
            tint: 0,
            href: "#holders",
          },
          {
            label: "Tickets",
            value: `${r.tickets_outstanding} outstanding`,
            icon: Inbox,
            tint: 2,
            href: "#holders",
          },
        ] satisfies RecordFact[])
      : ([
          {
            label: "About",
            value: r.linked_reference ?? "—",
            icon: FileText,
            tint: 0,
            href: r.linked_request?.in_scope
              ? `/requests/${r.linked_request.request_uuid}`
              : undefined,
          },
          {
            label: "With",
            value: r.about_dpo
              ? (r.reviewer_name ?? "Nobody yet")
              : "Data Protection Officer",
            icon: UserCheck,
            tint: 2,
          },
        ] satisfies RecordFact[])),
    erasure
      ? {
          label: "Items to decide",
          value: !r.item_count
            ? "None found yet"
            : r.items_undecided
              ? `${r.items_undecided} of ${r.item_count} undecided`
              : `All ${r.item_count} decided`,
          icon: ListChecks,
          tint: 1,
          href: "#scope",
        }
      : {
          label: "Identity",
          value: VERIFICATION_COPY[r.verification_status],
          icon: UserCheck,
          tint: 1,
          href: "#identity",
        },
  ];

  return (
    <>
      {/* The trail, then the request's summary card (2026-10-10, the detail
          look the user settled on): what it is and its state, over the four
          figures that say where the work stands. */}
      <PageHeader
        heading={false}
        breadcrumb={
          <Link href="/requests" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Rights requests
          </Link>
        }
        title={r.reference}
      />
      <RecordHeader
        icon={Scale}
        title={r.reference}
        meta={
          <>
            <span className="text-2xs font-semibold tracking-wider text-accent-text uppercase">
              Rights request
            </span>
            <RequestTypeBadge type={r.request_type} />
            <RequestStatusBadge status={r.status} outcome={r.outcome} />
            <span className="basis-full">
              {[typeCopy.label, typeCopy.section, humanise(r.channel), requester]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </>
        }
        actions={
          <AuditTrailLink
            entityType="rights_request"
            uuid={r.request_uuid}
            label={r.reference}
          />
        }
        facts={facts}
      />

      <Tabs value={tab} onValueChange={setTab} label="Request sections" layout="underline">
        <TabList>
          <Tab value="overview" icon={LayoutGrid}>
            Overview
          </Tab>
          <Tab value="identity" icon={UserCheck}>
            Identity &amp; classification
          </Tab>
          {withHolders && (
            <Tab value="holders" icon={Users} count={r.holder_count}>
              Holders
            </Tab>
          )}
          <Tab value="response" icon={Reply}>
            Response
          </Tab>
          <Tab value="history" icon={History}>
            History
          </Tab>
        </TabList>

        <TabPanel value="overview">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
            <div className="min-w-0 space-y-6">
              {/* `#actions`: where the next move points. First on the
                  overview, so marking a request In progress is the next
                  thing on the page (2026-10-07). */}
              {hasMoves && (
                <Group title="Next step" id="actions">
                  <RequestTransitions request={r} />
                </Group>
              )}

              <Group title="The request">
                <Card>
                  <CardBody>
                    <DescriptionList>
                      <DescriptionItem term="Who">
                        {r.subject_uuid ? (
                          <>
                            <Link
                              href={`/users?person=${r.subject_uuid}`}
                              className="text-accent-text hover:underline"
                            >
                              {r.subject_name}
                            </Link>
                            <span className="block text-xs text-text-subtle">
                              {r.subject_email}
                              {r.subject_mobile && ` · ${r.subject_mobile}`}
                            </span>
                          </>
                        ) : (
                          <>
                            <span>{r.submitted_name ?? "No name given"}</span>
                            <span className="block text-xs text-warning-text">
                              No account matches this contact
                            </span>
                          </>
                        )}
                      </DescriptionItem>
                      <DescriptionItem term="Contact given">
                        {r.submitted_contact}
                      </DescriptionItem>
                      {r.consent_uuid && (
                        <DescriptionItem term="Confined to">
                          <ConsentScope
                            scope={{
                              consent_uuid: r.consent_uuid,
                              project: r.consent_project,
                              notice_code: r.consent_notice_code,
                              notice_version: r.consent_notice_version,
                              at: r.consent_at,
                              withdrawn: r.consent_withdrawn,
                              purposes: r.consent_purposes,
                            }}
                          />
                          <span className="mt-1 block text-xs text-text-subtle">
                            The requester asked about this consent only. Holders, scope,
                            tickets and the response are confined to the data under it.
                          </span>
                        </DescriptionItem>
                      )}
                      <DescriptionItem term="Received">
                        {formatDateTime(r.received_at)}
                      </DescriptionItem>
                      <DescriptionItem term="Acknowledged">
                        {r.acknowledged_at ? formatDateTime(r.acknowledged_at) : "Not yet"}
                      </DescriptionItem>
                      {r.linked_reference && (
                        <DescriptionItem term="About">
                          <Mono>{r.linked_reference}</Mono>
                          <span className="ml-2 text-xs text-text-subtle">
                            {r.request_type === "grievance"
                              ? "the request under dispute, shown alongside"
                              : "shown alongside"}
                          </span>
                        </DescriptionItem>
                      )}
                      <LinkedFrom request={r} />
                      {r.channel === "nominee" && (
                        <DescriptionItem term="Nominee">
                          {r.nominee_name} ({r.nominee_contact}) ·{" "}
                          {r.trigger_event === "death"
                            ? "reports the principal has died"
                            : "reports the principal cannot act"}
                          {r.trigger_evidenced_at && (
                            <span className="block text-xs text-text-subtle">
                              Evidenced {formatDateTime(r.trigger_evidenced_at)}
                              {r.trigger_event === "death"
                                ? " · the principal's account is closed and cannot sign in"
                                : " · the principal keeps their account and can follow this request"}
                            </span>
                          )}
                          {r.trigger_evidence_hash && (
                            <a
                              className="ml-2 inline-flex items-center gap-1 text-accent-text underline underline-offset-2"
                              href={`${config.apiUrl}/requests/${r.request_uuid}/event/evidence`}
                            >
                              <Download className="size-3.5" aria-hidden="true" /> evidence
                            </a>
                          )}
                        </DescriptionItem>
                      )}
                      {r.about_dpo && (
                        <DescriptionItem term="Reviewer">
                          {r.reviewer_name ??
                            "Not yet assigned - an administrator names one"}
                        </DescriptionItem>
                      )}
                    </DescriptionList>
                    <p className="mt-4 rounded-md bg-bg-inset p-3 text-sm whitespace-pre-wrap">
                      {r.request_text}
                    </p>
                    <RequestDocuments request={r} />
                  </CardBody>
                </Card>

                {/* The clock and the path are the map of the request. Folded
                  to start with: the facts above carry the timing and the
                  card beside it the step, and the full map is there for
                  whoever wants to read it. Remembered per browser once
                  somebody opens it. */}
                <CollapsibleCard
                  title="Clock and path"
                  description="Every checkpoint this request runs to, and every step it takes - with where it can end early."
                  icon={Clock}
                  defaultOpen={false}
                  storageKey="request.overview"
                >
                  <div className="grid gap-6 p-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
                    <div className="min-w-0">
                      <h3 className="mb-3 text-sm font-semibold">Clock</h3>
                      <ClockColumn clock={r.clock} closed={closed} />
                    </div>
                    <div className="min-w-0">
                      <h3 className="mb-3 text-sm font-semibold">
                        The path, and where it can end early
                      </h3>
                      <Path request={r} />
                    </div>
                  </div>
                </CollapsibleCard>
              </Group>
            </div>

            <div className="min-w-0 space-y-5">
              <WhereItStands
                request={r}
                actionsHref={nextMoveIsResponse ? "#response" : "#actions"}
              />
              <LinkedRequestCard request={r} />
            </div>
          </div>
        </TabPanel>

        <TabPanel value="identity">
          <div className="grid gap-6 lg:grid-cols-2">
            <VerificationCard request={r} />
            <ClassificationCard request={r} />
          </div>
        </TabPanel>

        {withHolders && (
          <TabPanel value="holders" className="space-y-6">
            <HoldersCard request={r} />
            {erasure && (
              <div id="scope" className="scroll-mt-20">
                <ScopeCard request={r} />
              </div>
            )}
          </TabPanel>
        )}

        <TabPanel value="response">
          {responds ? (
            <RespondCard request={r} />
          ) : (
            <Card>
              <EmptyState
                title="Nothing to respond with yet"
                description={
                  r.request_type === "grievance"
                    ? "The decision opens once the grievance is taken up."
                    : "The response opens here once the server offers to respond, at the request's last step."
                }
              />
            </Card>
          )}
        </TabPanel>

        <TabPanel value="history">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="size-4" aria-hidden="true" />
                What was recorded
              </CardTitle>
            </CardHeader>
            <CardBody>
              <ActivityFeed
                entries={trail.data}
                isLoading={trail.isLoading}
                order="oldest"
                emptyTitle="Nothing recorded yet"
              />
            </CardBody>
          </Card>
        </TabPanel>
      </Tabs>
    </>
  );
}

/**
 * Where the request is on its path, who has it and the next move - the part
 * of the old summary strip the facts do not already say (2026-10-10).
 */
function WhereItStands({
  request: r,
  actionsHref,
}: {
  request: RightsRequestDetail;
  /** Where the controls that make the next move are on this page. */
  actionsHref: string;
}) {
  const closed = r.status === "closed";
  const current = stepsFor(r).find((s) => s.state === "current");
  const checkpoint = r.clock.checkpoints.find((c) => c.key === r.clock.next_checkpoint);
  const move = nextMove(r);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Where it stands</CardTitle>
      </CardHeader>
      <CardBody>
        <dl className="space-y-4">
          <div className="min-w-0">
            <dt className="text-xs text-text-subtle">Current step</dt>
            <dd className="mt-0.5">
              <span className="text-sm font-semibold">
                {closed ? "Closed" : (current?.title ?? STATUS_COPY[r.status].label)}
              </span>
              {!closed && current?.detail && (
                <span className="block text-xs text-text-muted">{current.detail}</span>
              )}
            </dd>
          </div>

          {!closed && !r.clock.overdue && checkpoint && (
            <div className="min-w-0">
              <dt className="text-xs text-text-subtle">Next checkpoint</dt>
              <dd className="mt-0.5 text-sm">
                {checkpoint.label}
                <span className="block text-xs text-text-muted">
                  by {formatDateTime(checkpoint.at)}
                </span>
              </dd>
            </div>
          )}

          <div className="min-w-0">
            <dt className="text-xs text-text-subtle">With</dt>
            <dd className="mt-0.5">
              {/* A complaint about the DPO is not theirs to answer; an
                  administrator names somebody else, and until then nobody has
                  it - which is worth saying rather than implying the DPO. */}
              <span className="text-sm font-semibold">
                {r.about_dpo
                  ? (r.reviewer_name ?? "Nobody yet")
                  : "Data Protection Officer"}
              </span>
              {r.about_dpo && (
                <span className="block text-xs text-text-muted">
                  {r.reviewer_name
                    ? "Reviewing a complaint about the DPO"
                    : "An administrator names a reviewer"}
                </span>
              )}
            </dd>
          </div>

          <div className="min-w-0">
            <dt className="text-xs text-text-subtle">Next</dt>
            <dd className="mt-0.5">
              {move ? (
                <>
                  <a
                    href={move.href ?? actionsHref}
                    className="inline-flex items-center gap-1 text-sm font-semibold text-accent-text hover:underline"
                  >
                    {move.label}
                    <ArrowDown className="size-3.5" aria-hidden="true" />
                  </a>
                  {move.blocked && (
                    <span className="mt-0.5 flex items-start gap-1 text-xs text-warning-text">
                      <AlertTriangle
                        className="mt-0.5 size-3 shrink-0"
                        aria-hidden="true"
                      />
                      {move.blocked}
                    </span>
                  )}
                </>
              ) : (
                <span className="text-sm text-text-muted">
                  {closed
                    ? "Nothing - a disagreement is a new, linked request"
                    : "Work the current step; the next move opens when it is done"}
                </span>
              )}
            </dd>
          </div>
        </dl>
      </CardBody>
    </Card>
  );
}

/** One group of the page, named so it can be found by eye and by heading. */
function Group({
  title,
  id,
  children,
}: {
  title: string;
  id?: string;
  children: React.ReactNode;
}) {
  const headingId = React.useId();
  return (
    <section id={id} aria-labelledby={headingId} className="scroll-mt-20 space-y-4">
      <h2
        id={headingId}
        className="text-sm font-semibold tracking-wide text-text-muted uppercase"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
