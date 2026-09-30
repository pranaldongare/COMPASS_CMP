/**
 * Notices about a personal data breach that may affect her data.
 *
 * Rule 7(1) says what she must be told, and names her account first among
 * the places she is told it. Each notice here says the five things in the
 * Rule's order; a later version is an update, sent when the facts changed,
 * and is shown above the earlier one. The notification that brought her here
 * is in her feed.
 */
"use client";

import { ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/layout/app-shell";
import { EmptyQueue } from "@/components/ui/graphics";
import { Alert, Card, CardBody, CardHeader, CardTitle, EmptyState, Skeleton } from "@/components/ui/primitives";
import { useMyBreachNotices } from "@/features/breach-notices";
import { formatDateTime } from "@/lib/format";
import type { MyBreachNotice } from "@/types";

const SECTIONS: Array<{ key: keyof MyBreachNotice; heading: string }> = [
  { key: "what_happened", heading: "What happened" },
  { key: "consequences", heading: "What it may mean for you" },
  { key: "measures", heading: "What we have done, and are doing" },
  { key: "protective_steps", heading: "What you can do" },
  { key: "contact", heading: "Questions" },
];

export default function BreachNoticesPage() {
  const query = useMyBreachNotices();
  const notices = query.data ?? [];

  return (
    <>
      <PageHeader
        title="Personal data breach notices"
        description="When a breach may affect your personal data, we tell you here and by your registered email or mobile: what happened, what it may mean for you, what we are doing, what you can do, and whom to ask."
      />

      {query.error && (
        <Alert tone="danger" title="Could not load your notices">
          {query.error.userMessage()}
        </Alert>
      )}
      {query.isLoading && <Skeleton className="h-48" />}
      {query.data && notices.length === 0 && (
        <Card>
          <EmptyState
            illustration={<EmptyQueue />}
            title="No notices"
            description="No personal data breach has been notified to you."
          />
        </Card>
      )}

      <div className="space-y-6">
        {notices.map((n) => (
          <Card key={n.notice_uuid}>
            <CardHeader>
              <CardTitle>
                <ShieldAlert className="mr-2 inline size-4" aria-hidden="true" />
                {n.reference}
                {n.version > 1 && ` - update ${n.version - 1}`}
              </CardTitle>
              <p className="mt-1 text-xs text-text-muted">Written to your account {formatDateTime(n.delivered_at)}</p>
            </CardHeader>
            <CardBody className="space-y-4">
              {SECTIONS.map((s) => (
                <section key={s.key}>
                  <h2 className="text-sm font-semibold">{s.heading}</h2>
                  <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{String(n[s.key])}</p>
                </section>
              ))}
            </CardBody>
          </Card>
        ))}
      </div>
    </>
  );
}
