/**
 * One processor, to read (2026-10-09).
 *
 * The register only offered Edit and Respondents. This is the processor as it
 * stands - what it is, where it is, its contract and security confirmation -
 * with the data sources it operates and who answers rights tickets for it.
 * Editing is a button here for those who may.
 */
"use client";

import { ArrowLeft, Pencil } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
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
import { StatusBadge } from "@/components/ui/status";
import { ProcessorForm } from "@/features/registry/components/forms";
import { RespondentsPanel } from "@/features/registry/components/respondents";
import { useProcessor, useSources } from "@/features/registry";
import { formatDate, formatDateTime, humanise } from "@/lib/format";
import { useAuth } from "@/providers";

export default function ProcessorDetailPage() {
  const { uuid } = useParams<{ uuid: string }>();
  const { me } = useAuth();
  const processor = useProcessor(uuid);
  const sources = useSources({ processor: uuid, limit: 100 });
  const [editing, setEditing] = React.useState(false);
  const canEdit = me?.role === "dpo" || me?.role === "admin";

  if (processor.error) {
    return (
      <>
        <PageHeader title="Processor" breadcrumb={<BackLink />} />
        <Alert tone="danger" title="Could not load this processor">
          {processor.error.isForbidden
            ? "You don't have access to this record."
            : processor.error.userMessage()}
        </Alert>
      </>
    );
  }
  if (processor.isLoading || !processor.data) {
    return (
      <>
        <PageHeader title="Processor" breadcrumb={<BackLink />} />
        <Skeleton className="h-80" />
      </>
    );
  }

  const p = processor.data;
  const operated = sources.data?.items ?? [];
  return (
    <>
      <PageHeader
        eyebrow="Processor"
        title={p.legal_name}
        description={`${humanise(p.type)} · ${p.is_in_house ? "in-house" : "a third party"}`}
        breadcrumb={<BackLink />}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge kind="record" value={p.status} />
            {canEdit && (
              <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="size-4" />
                Edit
              </Button>
            )}
          </div>
        }
      />

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>The processor</CardTitle>
          </CardHeader>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="Type">{humanise(p.type)}</DescriptionItem>
              <DescriptionItem term="Collects for">
                {p.is_in_house ? "Us - the organisation itself" : "Us, as a third party"}
              </DescriptionItem>
              <DescriptionItem term="Country">
                {p.location_country ? (
                  <span className="font-mono">{p.location_country}</span>
                ) : (
                  <span className="text-warning-text">
                    Not recorded - an export to this processor is refused until it is
                  </span>
                )}
              </DescriptionItem>
              <DescriptionItem term="Contract">
                <span className="font-mono">{p.contract_ref}</span>
              </DescriptionItem>
              <DescriptionItem term="Security confirmed">{formatDate(p.security_confirmed_at)}</DescriptionItem>
              <DescriptionItem term="Registered">{formatDateTime(p.created_at)}</DescriptionItem>
            </DescriptionList>
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <CardTitle>Data sources it operates</CardTitle>
            <span className="rounded-full bg-bg-inset px-2.5 py-0.5 text-xs font-medium tabular text-text-muted">
              {sources.data?.total ?? 0}
            </span>
          </CardHeader>
          <CardBody>
            {sources.isLoading ? (
              <Skeleton className="h-24" />
            ) : operated.length === 0 ? (
              <p className="text-sm text-text-muted">No data source names this processor.</p>
            ) : (
              <Table>
                <caption className="sr-only">Data sources this processor operates</caption>
                <thead>
                  <tr>
                    <Th>Source</Th>
                    <Th>Role</Th>
                    <Th>Status</Th>
                  </tr>
                </thead>
                <tbody>
                  {operated.map((s) => (
                    <Tr key={s.source_uuid}>
                      <Td>
                        <Link href={`/sources/${s.source_uuid}`} className="font-medium text-text hover:text-accent-text hover:underline">
                          {s.name}
                        </Link>
                        <p className="mt-0.5 font-mono text-xs text-text-subtle">{s.source_code}</p>
                      </Td>
                      <Td className="text-text-muted">{humanise(s.source_role)}</Td>
                      <Td>
                        <StatusBadge kind="record" value={s.status} />
                      </Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Who answers rights tickets</CardTitle>
          </CardHeader>
          <CardBody>
            <RespondentsPanel processor={p} />
          </CardBody>
        </Card>
      </div>

      <Dialog open={editing} onOpenChange={(o) => !o && setEditing(false)}>
        <DialogContent title="Edit processor" size="lg">
          {editing && <ProcessorForm processor={p} onDone={() => setEditing(false)} />}
        </DialogContent>
      </Dialog>
    </>
  );
}

function BackLink() {
  return (
    <Link href="/processors" className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text">
      <ArrowLeft className="size-4" aria-hidden="true" />
      Processors
    </Link>
  );
}
