/**
 * One data source, to read (2026-10-09).
 *
 * The register only offered Edit, so reading a source meant opening a form
 * that could change it. This is the record as it stands: who operates it, who
 * is accountable for collecting from it, how it exchanges data, and the fields
 * it is authoritative for. Editing is a button here for those who may.
 */
"use client";

import { ArrowLeft, Building2, Pencil } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Skeleton,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { SourceForm } from "@/features/registry/components/forms";
import { SourceOwner } from "@/features/registry/components/source-owner";
import { useSource } from "@/features/registry";
import { formatDateTime, humanise } from "@/lib/format";
import { useAuth } from "@/providers";

export default function SourceDetailPage() {
  const { uuid } = useParams<{ uuid: string }>();
  const { me } = useAuth();
  const source = useSource(uuid);
  const [editing, setEditing] = React.useState(false);
  // As on the register: the DPO and the administrator edit sources.
  const canEdit = me?.role === "dpo" || me?.role === "admin";

  if (source.error) {
    return (
      <>
        <PageHeader title="Data source" breadcrumb={<BackLink />} />
        <Alert tone="danger" title="Could not load this data source">
          {source.error.isForbidden
            ? "You don't have access to this record."
            : source.error.userMessage()}
        </Alert>
      </>
    );
  }
  if (source.isLoading || !source.data) {
    return (
      <>
        <PageHeader title="Data source" breadcrumb={<BackLink />} />
        <Skeleton className="h-80" />
      </>
    );
  }

  const s = source.data;
  return (
    <>
      <PageHeader
        eyebrow="Data source"
        title={s.name}
        description={s.source_code}
        breadcrumb={<BackLink />}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge kind="record" value={s.status} />
            {canEdit && (
              <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="size-4" />
                Edit
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Who runs it</CardTitle>
          </CardHeader>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="Processor">
                {s.processor_uuid && s.processor_name ? (
                  <Link href={`/processors/${s.processor_uuid}`} className="text-accent-text hover:underline">
                    {s.processor_name}
                  </Link>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-text-muted">
                    <Building2 className="size-3.5" aria-hidden="true" />
                    First party - the organisation runs it itself
                  </span>
                )}
              </DescriptionItem>
              <DescriptionItem term="Collected by">
                {s.is_in_house === null ? "Not known" : s.is_in_house ? "In-house" : "A third party"}
              </DescriptionItem>
              <DescriptionItem term="Accountable">
                <SourceOwner source={s} />
              </DescriptionItem>
            </DescriptionList>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>How it exchanges data</CardTitle>
          </CardHeader>
          <CardBody>
            <DescriptionList>
              <DescriptionItem term="Role">{humanise(s.source_role)}</DescriptionItem>
              <DescriptionItem term="Exchange">{humanise(s.exchange_mode)}</DescriptionItem>
              <DescriptionItem term="Identifier scheme">{s.id_scheme ?? "None"}</DescriptionItem>
              <DescriptionItem term="Authoritative for">
                {s.is_authoritative_for.length === 0 ? (
                  <span className="text-text-muted">Nothing - it never overwrites our values</span>
                ) : (
                  <span className="flex flex-wrap gap-1">
                    {s.is_authoritative_for.map((field) => (
                      <Badge key={field} tone="neutral" dot={false}>
                        {humanise(field)}
                      </Badge>
                    ))}
                  </span>
                )}
              </DescriptionItem>
              <DescriptionItem term="Registered">{formatDateTime(s.created_at)}</DescriptionItem>
            </DescriptionList>
          </CardBody>
        </Card>
      </div>

      <Dialog open={editing} onOpenChange={(o) => !o && setEditing(false)}>
        <DialogContent title="Edit data source" size="lg">
          {editing && <SourceForm source={s} onDone={() => setEditing(false)} />}
        </DialogContent>
      </Dialog>
    </>
  );
}

function BackLink() {
  return (
    <Link href="/sources" className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text">
      <ArrowLeft className="size-4" aria-hidden="true" />
      Data sources
    </Link>
  );
}
