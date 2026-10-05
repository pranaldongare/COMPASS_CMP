/**
 * One incident or breach: when it was noticed and where, its duties and their
 * clocks, validation, the assessment, and closing it. It is quoted by its
 * incident reference until a yes records it as a breach (S3-06).
 *
 * Duties come first because they are what runs out. Nothing on this page
 * decides what is due or whether the breach may close; every card renders the
 * server's answer.
 */
"use client";

import { ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AuditTrailLink } from "@/components/data-display/audit-link";
import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Button,
  Card,
  CardBody,
  DescriptionItem,
  DescriptionList,
  Skeleton,
} from "@/components/ui/primitives";
import { AffectedCard } from "@/features/breach/components/affected-card";
import {
  AssessmentCard,
  BreachTransitions,
  DeterminationCard,
  DutiesCard,
} from "@/features/breach/components/cards";
import { NoticesCard } from "@/features/breach/components/notices-card";
import { BreachStatusBadge, OutcomeBadge, locationText } from "@/features/breach/components/copy";
import { useBreach } from "@/features/breach/queries";
import { formatDateTime } from "@/lib/format";

export default function BreachPage() {
  const params = useParams<{ uuid: string }>();
  const breach = useBreach(params?.uuid);

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
              <Link href={`/breaches/${b.breach_uuid}/board`}>
                <FileText className="size-4" />
                Documents for the Board
              </Link>
            </Button>
            <AuditTrailLink entityType="breach" uuid={b.breach_uuid} label={b.reference} />
          </div>
        }
      />

      <div className="space-y-6">
        <Card>
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

        <DutiesCard breach={b} />
        <DeterminationCard breach={b} />
        <AffectedCard breach={b} />
        <NoticesCard breach={b} />
        <AssessmentCard breach={b} />
        <BreachTransitions breach={b} />
      </div>
    </>
  );
}
