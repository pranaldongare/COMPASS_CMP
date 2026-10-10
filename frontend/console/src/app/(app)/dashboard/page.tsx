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
 * single direct-labelled stacked bar. Nothing here is a pie, and nothing is a
 * one-bar bar chart pretending a number needs a plot.
 */
"use client";

import { OpenBreaches } from "@/features/breach/components/dashboard-breaches";
import { useRouter } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { BarList, StackedBar } from "@/components/ui/charts";

import { Alert, Card, CardBody, CardHeader, CardTitle } from "@/components/ui/primitives";

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
import { humanise } from "@/lib/format";
import { useAuth } from "@/providers";

export default function DashboardPage() {
  const { me } = useAuth();
  const router = useRouter();
  // An account the server gives no dashboard - a breach-only login (S3-09) -
  // lands on its tickets instead. Every way home leads here, so this is the
  // one place to send it on; the server's `nav` decides, not a role list.
  const elsewhere = Boolean(me && !me.nav.includes("dashboard") && me.nav.includes("tickets"));
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
  // the events that mean something. Eight is a glance, the trail is the rest.
  const recent = (data?.recent ?? [])
    .filter((e) => me?.role === "admin" || !e.event_type.startsWith("auth."))
    .slice(0, 8);

  return (
    <>
      <PageHeader
        hero
        eyebrow={me ? humanise(me.role) : undefined}
        title={me ? `Good day, ${me.full_name.split(" ")[0]}` : "Dashboard"}
        description={roleBlurb(me?.role)}
        actions={<QuickAction me={me} />}
      />

      {error && (
        <Alert tone="danger" title="Could not load the dashboard">
          {error.userMessage()}
        </Alert>
      )}

      {isLoading && <DashboardSkeleton />}

      {data && (
        <div className="space-y-6">
          {/* The summary first (2026-10-10): four figures for this role. Then,
              side by side on a desk, what needs a decision today and the
              position it sits in. Then the queues that hold the work. */}
          <KpiRow role={me?.role} counts={counts} />

          <div className="grid items-start gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <AttentionList rows={data.attention ?? []} />
            </div>

            {(lifecycle.length > 0 || composition) && (
              <div className="space-y-6" aria-label="The position">
                {composition && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Consent position</CardTitle>
                    </CardHeader>
                    <CardBody>
                      <StackedBar
                        segments={composition.segments}
                        caption="Every record counted once, at its current state."
                      />
                    </CardBody>
                  </Card>
                )}
                {lifecycle.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Projects by stage</CardTitle>
                    </CardHeader>
                    <CardBody>
                      <BarList items={lifecycle} emptyLabel="No projects registered yet." />
                      <p className="mt-4 text-xs text-text-subtle">
                        A project moves in one direction through these stages. Only an
                        approved project may collect consent.
                      </p>
                    </CardBody>
                  </Card>
                )}
              </div>
            )}
          </div>

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

