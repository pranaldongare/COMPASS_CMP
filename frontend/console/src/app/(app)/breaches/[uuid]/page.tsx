/**
 * One breach: when it was noticed and where, its duties and their clocks, the
 * determination, the assessment, and closing it.
 *
 * Duties come first because they are what runs out. Nothing on this page
 * decides what is due or whether the breach may close; every card renders the
 * server's answer.
 */
"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AuditTrailLink } from "@/components/data-display/audit-link";
import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Card,
  CardBody,
  DescriptionItem,
  DescriptionList,
  Skeleton,
} from "@/components/ui/primitives";
import {
  AssessmentCard,
  BreachTransitions,
  DeterminationCard,
  DutiesCard,
} from "@/features/breach/components/cards";
import { BreachStatusBadge, OutcomeBadge, locationText } from "@/features/breach/components/copy";
import { useBreach } from "@/features/breach/queries";
import { formatDateTime } from "@/lib/format";

export default function BreachPage() {
  const params = useParams<{ uuid: string }>();
  const breach = useBreach(params?.uuid);

  if (breach.isLoading) return <Skeleton className="h-96" />;
  if (breach.error) {
    return (
      <Alert tone="danger" title="Could not load this breach">
        {breach.error.userMessage()}
      </Alert>
    );
  }
  const b = breach.data;
  if (!b) return null;

  return (
    <>
      <PageHeader
        eyebrow="Personal data breach"
        breadcrumb={
          <Link href="/breaches" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Breaches
          </Link>
        }
        title={b.reference}
        description={b.title}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <OutcomeBadge outcome={b.determination} />
            <BreachStatusBadge status={b.status} />
            <AuditTrailLink entityType="breach" uuid={b.breach_uuid} label={b.reference} />
          </div>
        }
      />

      <div className="space-y-6">
        <Card>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="First noticed">{formatDateTime(b.detected_at)}</DescriptionItem>
              <DescriptionItem term="Became aware">
                {b.became_aware_at ? formatDateTime(b.became_aware_at) : "Set with a determination of yes"}
              </DescriptionItem>
              <DescriptionItem term="Began">{b.began_at ? formatDateTime(b.began_at) : "Not known"}</DescriptionItem>
              <DescriptionItem term="Where">
                {locationText(b.location)}
                {b.location.detail && <span className="block whitespace-pre-wrap text-sm">{b.location.detail}</span>}
              </DescriptionItem>
              <DescriptionItem term="Recorded">
                {formatDateTime(b.recorded_at)} by {b.recorded_by_name ?? "unknown"}
              </DescriptionItem>
            </DescriptionList>
          </CardBody>
        </Card>

        <DutiesCard breach={b} />
        <DeterminationCard breach={b} />
        <AssessmentCard breach={b} />
        <BreachTransitions breach={b} />
      </div>
    </>
  );
}
