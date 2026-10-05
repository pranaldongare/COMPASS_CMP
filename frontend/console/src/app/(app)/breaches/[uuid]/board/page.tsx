/**
 * The Board's two documents for one breach, drafted from the register (S3-04).
 *
 * Rule 7(2)(a), the initial intimation, and 7(2)(b), the detailed report with
 * its six items. Drafted by the server each time the page is opened, so what
 * is shown is what the register holds now; a fact it does not hold yet is
 * named rather than left blank. The platform never submits either: the DPO
 * files through the Board's own channel and records the submission, with the
 * Board's reference, on the breach's duties.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Printer } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

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
import { getIntimation, getReport } from "@/features/breach/api";
import { OUTCOME_COPY, clockText, locationText } from "@/features/breach/components/copy";
import { formatDateTime } from "@/lib/format";
import type { BreachDuty, BreachIntimation, BreachReport } from "@/types";

const CHANNEL: Record<string, string> = { portal: "Their account", email: "Email", sms: "SMS" };

function Missing({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <Alert tone="warning" title="Not yet in the register">
      <ul className="list-disc pl-5">
        {items.map((m) => (
          <li key={m}>{m}</li>
        ))}
      </ul>
    </Alert>
  );
}

function DutyLine({ duty }: { duty: BreachDuty | null }) {
  if (!duty) return <p className="text-sm text-text-muted">This duty arises with a validation of yes.</p>;
  return (
    <p className="text-sm">
      <strong>{duty.label}</strong> ({duty.basis}):{" "}
      {duty.state === "done"
        ? `submitted ${formatDateTime(duty.completed_at)}, reference ${duty.reference}`
        : duty.state === "not_applicable"
          ? "not applicable"
          : `${duty.due_at ? `due ${formatDateTime(duty.due_at)}` : "due without delay"} - ${clockText(duty.state, duty.clock)}`}
    </p>
  );
}

function Timing({ doc }: { doc: BreachIntimation | BreachReport }) {
  return (
    <>
      <DescriptionItem term="Reference">{doc.reference}</DescriptionItem>
      <DescriptionItem term="Validation">{OUTCOME_COPY[doc.determination]}</DescriptionItem>
      <DescriptionItem term="First noticed">{formatDateTime(doc.detected_at)}</DescriptionItem>
      <DescriptionItem term="Became aware">
        {doc.became_aware_at ? formatDateTime(doc.became_aware_at) : "Set with a validation of yes"}
      </DescriptionItem>
      <DescriptionItem term="Began">{doc.began_at ? formatDateTime(doc.began_at) : "Not known"}</DescriptionItem>
      <DescriptionItem term="Where it occurred">
        {locationText(doc.location)}
        {doc.location.detail && <span className="block whitespace-pre-wrap">{doc.location.detail}</span>}
      </DescriptionItem>
    </>
  );
}

function Text({ value }: { value: string | null | undefined }) {
  return value ? <span className="whitespace-pre-wrap">{value}</span> : <em className="text-text-muted">Not recorded</em>;
}

function Intimation({ doc }: { doc: BreachIntimation }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Initial intimation - {doc.basis}</CardTitle>
        <p className="mt-1 text-xs text-text-muted">Drafted {formatDateTime(doc.generated_at)} from the register.</p>
      </CardHeader>
      <CardBody className="space-y-4">
        <Missing items={doc.missing} />
        <DescriptionList>
          <Timing doc={doc} />
          <DescriptionItem term="Nature and extent">
            <Text value={doc.nature_extent} />
          </DescriptionItem>
          <DescriptionItem term="Likely impact">
            <Text value={doc.likely_impact} />
          </DescriptionItem>
        </DescriptionList>
        <DutyLine duty={doc.duty} />
      </CardBody>
    </Card>
  );
}

function Report({ doc }: { doc: BreachReport }) {
  const a = doc.assessment;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Detailed report - {doc.basis}</CardTitle>
        <p className="mt-1 text-xs text-text-muted">Drafted {formatDateTime(doc.generated_at)} from the register.</p>
      </CardHeader>
      <CardBody className="space-y-6">
        <Missing items={doc.missing} />
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">(i) Updated and detailed information</h2>
          <DescriptionList>
            <Timing doc={doc} />
            <DescriptionItem term="Nature and extent">
              <Text value={a?.nature_extent} />
            </DescriptionItem>
            <DescriptionItem term="Likely impact">
              <Text value={a?.likely_impact} />
            </DescriptionItem>
            <DescriptionItem term="Consequences for the people affected">
              <Text value={a?.consequences} />
            </DescriptionItem>
            <DescriptionItem term="Data categories">
              {a && a.categories.length > 0 ? (
                <ul>
                  {a.categories.map((c) => (
                    <li key={c.category}>
                      {c.category} - {c.sealed ? (c.key_exposed ? "sealed, key exposed" : "sealed, key safe") : "not sealed"}
                    </li>
                  ))}
                </ul>
              ) : (
                <em className="text-text-muted">Not recorded</em>
              )}
            </DescriptionItem>
            <DescriptionItem term="Assessment">
              {a ? `Revision ${a.revision} of ${doc.assessment_revisions}, ${formatDateTime(a.revised_at)}` : "None yet"}
            </DescriptionItem>
            <DescriptionItem term="Determinations">
              <ol className="space-y-1">
                {doc.determinations.map((d) => (
                  <li key={d.determination_uuid}>
                    {formatDateTime(d.determined_at)}: {OUTCOME_COPY[d.outcome]} - <Text value={d.reasoning} />
                  </li>
                ))}
              </ol>
            </DescriptionItem>
          </DescriptionList>
        </section>
        {doc.facts.map((f) => (
          <section key={f.item} className="space-y-1">
            <h2 className="text-sm font-semibold">
              ({f.item}) {f.label}
            </h2>
            <p className="text-sm">
              <Text value={f.text} />
            </p>
          </section>
        ))}
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">(vi) The account of notices to the Data Principals affected</h2>
          <p className="text-sm">{doc.notices.statement}</p>
          {doc.notices.versions.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Version</Th>
                  <Th>Approved</Th>
                  <Th>Channel</Th>
                  <Th>Delivered</Th>
                  <Th>Queued</Th>
                  <Th>Failed</Th>
                </tr>
              </thead>
              <tbody>
                {doc.notices.versions.flatMap((v) =>
                  v.channels.map((c) => (
                    <Tr key={`${v.version}:${c.channel}`}>
                      <Td>{v.version}</Td>
                      <Td>{formatDateTime(v.approved_at)}</Td>
                      <Td>{CHANNEL[c.channel]}</Td>
                      <Td>{c.delivered}</Td>
                      <Td>{c.queued}</Td>
                      <Td>{c.failed}</Td>
                    </Tr>
                  )),
                )}
              </tbody>
            </Table>
          )}
        </section>
        <DutyLine duty={doc.duty} />
      </CardBody>
    </Card>
  );
}

export default function BoardDocumentsPage() {
  const params = useParams<{ uuid: string }>();
  const uuid = params?.uuid ?? "";
  const intimation = useQuery({ queryKey: ["breach", uuid, "board", "intimation"], queryFn: () => getIntimation(uuid), enabled: Boolean(uuid) });
  const report = useQuery({ queryKey: ["breach", uuid, "board", "report"], queryFn: () => getReport(uuid), enabled: Boolean(uuid) });

  return (
    <>
      <PageHeader
        eyebrow="Personal data breach"
        breadcrumb={
          <Link href={`/breaches/${uuid}`} className="inline-flex items-center gap-1 hover:underline print:hidden">
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            The breach
          </Link>
        }
        title={`Documents for the Board${intimation.data ? ` - ${intimation.data.reference}` : ""}`}
        description="Drafted from the register as it stands. The platform does not submit them: file each through the Board's own channel, then record the submission and the Board's reference on the breach's duties."
        actions={
          <Button variant="secondary" className="print:hidden" onClick={() => window.print()}>
            <Printer className="size-4" />
            Print
          </Button>
        }
      />
      {(intimation.isLoading || report.isLoading) && <Skeleton className="h-96" />}
      {(intimation.error || report.error) && (
        <Alert tone="danger" title="Could not draft the documents">
          The server refused.
        </Alert>
      )}
      <div className="space-y-6">
        {intimation.data && <Intimation doc={intimation.data} />}
        {report.data && <Report doc={report.data} />}
      </div>
    </>
  );
}
