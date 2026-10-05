/**
 * The brief for the organisation's board (S3-07).
 *
 * Internal policy asks that the board hear of an incident within thirty
 * minutes of its being first noticed. This page drafts what to tell it from
 * the register as it stands - from the incident's first minutes on, before
 * validation has said anything - names what the register does not hold yet,
 * and prints. It carries no finding on who caused it and nobody's name: who
 * it touched is counts. The platform never reports to the board; a person
 * does, and the DPO records when and to whom on the duty.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Printer } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

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
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { getOrgBoardBrief } from "@/features/breach/api";
import { OUTCOME_COPY, clockText, locationText } from "@/features/breach/components/copy";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";

export default function OrgBoardBriefPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params?.uuid ?? "";
  const brief = useQuery({
    queryKey: keys.breach.orgBoard(uuid),
    queryFn: () => getOrgBoardBrief(uuid),
    enabled: Boolean(uuid),
  });
  const doc = brief.data;

  return (
    <>
      <PageHeader
        eyebrow={doc?.breach_reference ? "Personal data breach" : "Incident"}
        breadcrumb={
          <Link href={`/breaches/${uuid}`} className="inline-flex items-center gap-1 hover:underline print:hidden">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Back to the incident
          </Link>
        }
        title={`Brief for the organisation's board${doc ? ` - ${doc.reference}` : ""}`}
        description="Drafted from the register as it stands. The platform does not report to the board: tell it through the organisation's own channel, then record when and to whom on the incident's duties."
        actions={
          <Button variant="secondary" className="print:hidden" onClick={() => window.print()}>
            <Printer className="size-4" />
            Print
          </Button>
        }
      />
      {brief.isLoading && <Skeleton className="h-96" />}
      {brief.error && (
        <Alert tone="danger" title="Could not draft the brief">
          {brief.error.message}
        </Alert>
      )}
      {doc && (
        <Card>
          <CardHeader>
            <CardTitle>{doc.basis}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">Drafted {formatDateTime(doc.generated_at)} from the register.</p>
          </CardHeader>
          <CardBody className="space-y-6">
            {doc.missing.length > 0 && (
              <Alert tone="warning" title="Not yet in the register">
                <ul className="list-disc pl-5">
                  {doc.missing.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </Alert>
            )}
            <DescriptionList>
              <DescriptionItem term="Reference">
                {doc.reference}
                {doc.breach_reference && doc.incident_reference !== doc.breach_reference && (
                  <span className="block text-xs text-text-subtle">logged as {doc.incident_reference}</span>
                )}
              </DescriptionItem>
              <DescriptionItem term="What">{doc.title}</DescriptionItem>
              <DescriptionItem term="First noticed">{formatDateTime(doc.detected_at)}</DescriptionItem>
              <DescriptionItem term="Began">{doc.began_at ? formatDateTime(doc.began_at) : "Not known"}</DescriptionItem>
              <DescriptionItem term="Where it occurred">
                {locationText(doc.location)}
                {doc.location.detail && <span className="block whitespace-pre-wrap">{doc.location.detail}</span>}
              </DescriptionItem>
              <DescriptionItem term="Validation">
                {OUTCOME_COPY[doc.validation]}
                {doc.became_aware_at && (
                  <span className="block text-xs text-text-subtle">aware {formatDateTime(doc.became_aware_at)}</span>
                )}
              </DescriptionItem>
              <DescriptionItem term="Reportable to CERT-In">{doc.cert_in_reportable ? "Yes, marked" : "Not marked"}</DescriptionItem>
              <DescriptionItem term="Who it touched">
                {doc.touched.listed === 0
                  ? "No list confirmed yet"
                  : `${doc.touched.listed} listed; ${doc.touched.notified} notified on every channel`}
              </DescriptionItem>
            </DescriptionList>
            <section className="space-y-2">
              <h2 className="text-sm font-semibold">Duties and their clocks</h2>
              <Table>
                <thead>
                  <tr>
                    <Th>Duty</Th>
                    <Th>Due</Th>
                    <Th>Where it stands</Th>
                  </tr>
                </thead>
                <tbody>
                  {doc.duties.map((d) => (
                    <Tr key={d.duty}>
                      <Td>
                        <span className="font-medium">{d.label}</span>
                        <span className="block text-xs text-text-subtle">{d.basis}</span>
                      </Td>
                      <Td>{d.due_at ? formatDateTime(d.due_at) : "Without delay"}</Td>
                      <Td className="text-sm">
                        {d.state === "done"
                          ? `Done ${formatDateTime(d.completed_at)}`
                          : d.state === "not_applicable"
                            ? "Not applicable"
                            : clockText(d.state, d.clock)}
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </section>
          </CardBody>
        </Card>
      )}
    </>
  );
}
