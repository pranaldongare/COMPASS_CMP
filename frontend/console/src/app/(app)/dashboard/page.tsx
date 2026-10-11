/**
 * The dashboard.
 *
 * One endpoint, role-aware. The response shape differs by role but the call does
 * not, so there is one loading path here rather than five components each
 * fetching something different.
 *
 * The work queues matter more than the counts. A DPO opening this page needs to
 * know what is waiting for *her*, not how many projects exist — so the queues
 * sit above the fold and the figures support them.
 *
 * On the charts: a count that a chart already explains is not repeated as a
 * tile. The project lifecycle is a magnitude comparison across named stages, so
 * it is a one-hue bar list; the consent position is part-to-whole, so it is a
 * ring with a direct-labelled legend (2026-10-10, the role-dashboard design).
 *
 * The layout is the approved role-dashboard design: a greeting banner with the
 * date and the role's start, four figures, then Needs attention beside the
 * position on a 12-column grid, the queues two to a row, and recent activity.
 */
"use client";

import { OpenBreaches } from "@/features/breach/components/dashboard-breaches";
import { useRouter } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { CalendarDays, FileCheck, FolderKanban } from "lucide-react";

import { BarList, Donut } from "@/components/ui/charts";
import { PanelHeader } from "@/components/ui/panel";
import { Alert, Card, CardBody } from "@/components/ui/primitives";

import { useDashboard } from "@/features/dashboard";
import {
  AttentionList,
  COUNT_LABELS,
  ClearQueues,
  DashboardSkeleton,
  LIFECYCLE,
  QueueCard,
  RecentCard,
  consentComposition,
  roleBlurb,
} from "@/features/dashboard/components";
import { KpiRow } from "@/features/dashboard/components/kpi-row";
import { QuickAction } from "@/features/dashboard/components/quick-action";
import { statusLabel } from "@/components/ui/status";
import { useAuth } from "@/providers";

/** The banner's kicker: the role in full (2026-10-11, the design), where the
 *  badge elsewhere uses the short form ("DPO"). */
const ROLE_TITLE: Record<string, string> = {
  dpo: "Data Protection Officer",
  admin: "Administrator",
};

export default function DashboardPage() {
  const { me } = useAuth();
  const router = useRouter();
  // An account the server gives no dashboard - a breach-only login (S3-09) -
  // lands on its tickets instead. Every way home leads here, so this is the
  // one place to send it on; the server's `nav` decides, not a role list.
  const elsewhere = Boolean(
    me && !me.nav.includes("dashboard") && me.nav.includes("tickets"),
  );
  React.useEffect(() => {
    if (elsewhere) router.replace("/tickets");
  }, [elsewhere, router]);
  const { data, isLoading, error } = useDashboard();

  const counts = data?.counts ?? {};
  const lifecycle = LIFECYCLE.filter((k) => k in counts).map((k) => ({
    key: k,
    label: COUNT_LABELS[k],
    value: counts[k],
    href: `/projects?status=${k}`,
  }));
  const composition = consentComposition(counts);
  const queues = data?.queues ?? [];
  const busy = queues.filter((q) => q.items.length > 0);
  const clear = queues.filter((q) => q.items.length === 0).map((q) => q.name);
  // Sign-ins are the administrator's business; for everyone else they bury
  // the events that mean something. Five is a glance, the trail is the rest.
  const recent = (data?.recent ?? [])
    .filter((e) => me?.role === "admin" || !e.event_type.startsWith("auth."))
    .slice(0, 5);

  // The position card beside Needs attention: the consent ring where the role
  // has one, the project stages otherwise. A DPO has both; the stages then
  // join the queues below rather than stacking a second card here.
  const consentCard = composition && (
    <Card className="flex h-full flex-col overflow-hidden rounded-2xl">
      <PanelHeader
        icon={FileCheck}
        tint={2}
        title="Consent position"
        link={
          me?.nav.includes("consents") ? { href: "/consents", label: "Open" } : undefined
        }
      />
      <CardBody className="flex flex-1 items-center px-[22px] py-[18px]">
        <div className="w-full">
          <Donut segments={composition.segments} centreLabel="records" />
        </div>
      </CardBody>
    </Card>
  );
  const stagesCard = lifecycle.length > 0 && (
    <Card className="flex h-full flex-col overflow-hidden rounded-2xl">
      <PanelHeader
        icon={FolderKanban}
        title="Projects by stage"
        link={{ href: "/projects", label: "Open" }}
      />
      <CardBody className="flex flex-1 flex-col justify-center gap-3 px-[18px]">
        <BarList items={lifecycle} emptyLabel="No projects registered yet." />
        <p className="text-xs text-text-subtle">
          A project moves one way through these stages; only an approved one may collect
          consent.
        </p>
      </CardBody>
    </Card>
  );
  const position = consentCard || stagesCard;
  const today = new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date());

  return (
    <>
      <PageHeader
        hero
        eyebrow={me ? (ROLE_TITLE[me.role] ?? statusLabel("role", me.role)) : undefined}
        title={me ? `Good day, ${me.full_name.split(" ")[0]}` : "Dashboard"}
        description={roleBlurb(me?.role)}
        actions={
          <>
            <span className="hidden h-9 items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 text-xs whitespace-nowrap text-text-muted md:inline-flex">
              <CalendarDays className="size-3.5" aria-hidden="true" />
              {today}
            </span>
            <QuickAction me={me} />
          </>
        }
      />

      {error && (
        <Alert tone="danger" title="Could not load the dashboard">
          {error.userMessage()}
        </Alert>
      )}

      {isLoading && <DashboardSkeleton />}

      {data && (
        <div className="space-y-4">
          <KpiRow role={me?.role} counts={counts} />

          {/* Needs attention beside the position: seven and five of twelve,
              the two cards one height. */}
          <div className="grid items-stretch gap-4 lg:grid-cols-12">
            <div className={position ? "lg:col-span-7" : "lg:col-span-12"}>
              <AttentionList rows={data.attention ?? []} />
            </div>
            {position && (
              <div className="lg:col-span-5" aria-label="The position">
                {position}
              </div>
            )}
          </div>

          {/* The queues, two to a row, each card the height of its pair. */}
          {(busy.length > 0 ||
            (data.breaches?.length ?? 0) > 0 ||
            (consentCard && stagesCard)) && (
            <div className="grid items-stretch gap-4 lg:grid-cols-2">
              <OpenBreaches breaches={data.breaches ?? []} />
              {busy.map((queue) => (
                <QueueCard
                  key={queue.name}
                  name={queue.name}
                  items={queue.items}
                  slug={queue.slug}
                  href={queue.href}
                  capped={queue.capped}
                />
              ))}
              {consentCard && stagesCard}
            </div>
          )}
          <ClearQueues names={clear} />

          {/* Rendered even when empty: the panel's empty state says activity
              will appear here, which is more use to somebody on their first day
              than an absent section they never learn exists. */}
          <RecentCard
            items={recent}
            // Only the roles with an audit page get the link. A DCO following
            // one would land on a 403.
            seeAllHref={me?.nav.includes("audit") ? "/audit" : undefined}
          />
        </div>
      )}
    </>
  );
}
