/**
 * One incident or breach, as one workspace - the project page's shape.
 *
 * Above the tabs, where it stands: closing (or reopening) it, with exactly
 * what still stands in the way, beside the facts it was logged with. Under
 * the tabs, the work in the order it runs: the duties and their clocks first,
 * because they are what runs out; then validation, who it touched and what
 * they are told, the tickets, the assessment, the files kept with it
 * (2026-10-06), and its history. A tab whose
 * duties are late says so from whichever tab is open.
 *
 * The fragment names the tab, so a tab can be linked to and survives a
 * reload; the anchors of the cards inside a tab open it too, which keeps
 * `#tickets` - the bell's link for a holder's answer - landing on the card.
 * It is quoted by its incident reference until a yes records it as a breach
 * (S3-06). Nothing on this page decides what is due or whether the breach may
 * close; every card renders the server's answer.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, FileText, History as HistoryIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { AuditTrailLink } from "@/components/data-display/audit-link";
import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Skeleton,
} from "@/components/ui/primitives";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import { listBreachTickets } from "@/features/breach/api";
import { AffectedCard } from "@/features/breach/components/affected-card";
import { AttachmentsCard } from "@/features/breach/components/attachments";
import {
  AssessmentCard,
  BreachTransitions,
  DeterminationCard,
  DutiesCard,
} from "@/features/breach/components/cards";
import { BreachStatusBadge, OutcomeBadge, locationText } from "@/features/breach/components/copy";
import { NoticesCard } from "@/features/breach/components/notices-card";
import { TicketsCard } from "@/features/breach/components/tickets-card";
import { useBreach } from "@/features/breach/queries";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import type { Breach } from "@/types";

const TABS = ["duties", "validation", "people", "tickets", "assessment", "attachments", "activity"] as const;
type BreachTab = (typeof TABS)[number];
/** Card anchors inside a tab, written before the tabs or naming one card. */
const SECTIONS: Record<string, BreachTab> = {
  affected: "people",
  notices: "people",
  history: "activity",
};

export default function BreachPage() {
  const params = useParams<{ uuid: string }>();
  const breach = useBreach(params?.uuid);
  const [tab, setTab, hash] = useHashTab(TABS, "duties", SECTIONS);
  const loaded = Boolean(breach.data);
  // A fragment naming a card, not a tab: the tab is open by now, so bring the
  // card itself into view - the browser's own jump ran before it existed.
  React.useEffect(() => {
    if (!loaded || !Object.hasOwn(SECTIONS, hash)) return;
    document.getElementById(hash)?.scrollIntoView?.({ block: "start" });
  }, [hash, loaded]);
  // The same query the Tickets card runs, for the tab's count.
  const tickets = useQuery({
    queryKey: keys.breach.tickets(params?.uuid ?? ""),
    queryFn: () => listBreachTickets(params?.uuid ?? ""),
    enabled: Boolean(params?.uuid),
  });

  if (breach.isLoading) return <Skeleton className="h-96" />;
  if (breach.error) {
    return (
      <Alert tone="danger" title="Could not load this incident">
        {breach.error.userMessage()}
      </Alert>
    );
  }
  const b = breach.data;
  if (!b) return null;

  const outstanding = b.obligations.filter((d) => d.state === "outstanding");
  const late = outstanding.filter((d) => d.clock.overdue || d.clock.past_target).length;
  const openTickets = (tickets.data ?? []).filter((t) => t.state === "issued" || t.state === "returned");
  const ticketsLate = openTickets.filter((t) => t.overdue).length;

  return (
    <>
      <PageHeader
        eyebrow={b.breach_reference ? "Personal data breach" : "Incident, being validated"}
        breadcrumb={
          <Link href="/breaches" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Incidents and breaches
          </Link>
        }
        title={b.reference}
        description={b.title}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <OutcomeBadge outcome={b.determination} />
            <BreachStatusBadge status={b.status} />
            <Button variant="secondary" size="sm" asChild>
              <Link href={`/breaches/${b.breach_uuid}/org-board`}>
                <FileText className="size-4" />
                Brief for the organisation&apos;s board
              </Link>
            </Button>
            <Button variant="secondary" size="sm" asChild>
              <Link href={`/breaches/${b.breach_uuid}/board`}>
                <FileText className="size-4" />
                Documents for the Board
              </Link>
            </Button>
            <AuditTrailLink entityType="breach" uuid={b.breach_uuid} label={b.reference} />
          </div>
        }
      />

      {/* Where it stands before anything else: closing it, or exactly what
          still stands in the way, beside the facts it was logged with.
          Everything under the tabs is the work behind it. On a phone the
          facts follow the tabs, so the work is not a screen's scroll away. */}
      <div className="mb-6 grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 lg:col-span-2">
          <BreachTransitions breach={b} />
        </div>
        <div className="hidden min-w-0 lg:block">
          <DetailsCard breach={b} />
        </div>
      </div>

      {/* The step that starts the statutory clocks, wherever the reader is. */}
      {b.status === "open" && b.determination === "pending" && tab !== "validation" && (
        <Alert tone="info" title="Not validated yet" className="mb-6">
          Is it a personal data breach under s.2(u)? A yes records it and starts the DPDP duties.{" "}
          <a href="#validation" className="font-medium text-accent-text hover:underline">
            Record the validation
          </a>
        </Alert>
      )}

      <Tabs value={tab} onValueChange={setTab} label="Breach sections">
        <TabList>
          <Tab
            value="duties"
            count={outstanding.length}
            alert={late ? `${late} late` : undefined}
          >
            Duties
          </Tab>
          <Tab value="validation" count={b.determinations.length}>
            Validation
          </Tab>
          <Tab value="people">People &amp; notices</Tab>
          <Tab
            value="tickets"
            count={tickets.data ? openTickets.length : undefined}
            alert={ticketsLate ? `${ticketsLate} past their answer-by` : undefined}
          >
            Tickets
          </Tab>
          <Tab value="assessment" count={b.assessment_revisions}>
            Assessment
          </Tab>
          <Tab value="attachments" count={b.attachments.length}>
            Attachments
          </Tab>
          <Tab value="activity" count={b.status_history.length}>
            Activity
          </Tab>
        </TabList>

        <TabPanel value="duties" className="space-y-6">
          <DutiesCard breach={b} />
        </TabPanel>
        <TabPanel value="validation" className="space-y-6">
          <DeterminationCard breach={b} />
        </TabPanel>
        <TabPanel value="people" className="space-y-6">
          <div id="affected" className="scroll-mt-20">
            <AffectedCard breach={b} />
          </div>
          <div id="notices" className="scroll-mt-20">
            <NoticesCard breach={b} />
          </div>
        </TabPanel>
        <TabPanel value="tickets" className="space-y-6">
          <TicketsCard breach={b} />
        </TabPanel>
        <TabPanel value="assessment" className="space-y-6">
          <AssessmentCard breach={b} />
        </TabPanel>
        <TabPanel value="attachments" className="space-y-6">
          <AttachmentsCard breach={b} />
        </TabPanel>
        <TabPanel value="activity" className="space-y-6">
          <HistoryCard breach={b} />
        </TabPanel>
      </Tabs>

      <div className="mt-6 lg:hidden">
        <DetailsCard breach={b} />
      </div>
    </>
  );
}

function DetailsCard({ breach: b }: { breach: Breach }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Details</CardTitle>
      </CardHeader>
      <CardBody>
        <DescriptionList>
          {b.breach_reference && b.incident_reference !== b.breach_reference && (
            <DescriptionItem term="Logged as">{b.incident_reference}</DescriptionItem>
          )}
          <DescriptionItem term="Recorded as a breach">
            {b.breach_recorded_at
              ? `${formatDateTime(b.breach_recorded_at)} by ${b.breach_recorded_by_name ?? "unknown"}`
              : "Not yet: a validation of yes records it"}
          </DescriptionItem>
          <DescriptionItem term="First noticed">{formatDateTime(b.detected_at)}</DescriptionItem>
          <DescriptionItem term="Became aware">
            {b.became_aware_at ? formatDateTime(b.became_aware_at) : "Set with a validation of yes"}
          </DescriptionItem>
          <DescriptionItem term="Began">{b.began_at ? formatDateTime(b.began_at) : "Not known"}</DescriptionItem>
          <DescriptionItem term="Where">
            {locationText(b.location)}
            {b.location.detail && <span className="block whitespace-pre-wrap text-sm">{b.location.detail}</span>}
          </DescriptionItem>
          <DescriptionItem term="Logged">
            {formatDateTime(b.recorded_at)} by {b.recorded_by_name ?? "unknown"}
          </DescriptionItem>
        </DescriptionList>
      </CardBody>
    </Card>
  );
}

/** Every open, close and reopening, with the reason a reopening gives. */
function HistoryCard({ breach: b }: { breach: Breach }) {
  return (
    <Card id="history" className="scroll-mt-20">
      <CardHeader className="flex items-center justify-between">
        <div>
          <CardTitle>History</CardTitle>
          <p className="mt-0.5 text-xs text-text-muted">
            Append-only. Every close and reopening, who made it, and why. Everything else done to it is in the audit
            trail.
          </p>
        </div>
        <HistoryIcon className="size-4 text-text-subtle" aria-hidden="true" />
      </CardHeader>
      {b.status_history.length === 0 ? (
        <CardBody>
          <p className="text-sm text-text-muted">Nothing yet.</p>
        </CardBody>
      ) : (
        <ol className="divide-y divide-border">
          {[...b.status_history].reverse().map((entry) => (
            <li key={`${entry.changed_at}-${entry.to_status}`} className="px-5 py-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                {entry.from_status ? (
                  <>
                    <BreachStatusBadge status={entry.from_status} />
                    <span aria-hidden="true" className="text-text-subtle">
                      →
                    </span>
                  </>
                ) : (
                  <span className="text-text-subtle">Logged as</span>
                )}
                <BreachStatusBadge status={entry.to_status} />
              </div>
              <p className="mt-1 text-xs text-text-muted">
                {entry.changed_by_name ?? "Unknown"} · {formatDateTime(entry.changed_at)}
              </p>
              {entry.reason && (
                <p className="mt-1 rounded bg-bg-inset px-2 py-1 text-xs text-text">“{entry.reason}”</p>
              )}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
