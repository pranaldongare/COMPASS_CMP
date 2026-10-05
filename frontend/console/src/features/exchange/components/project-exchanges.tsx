/**
 * One project's collections and exports, for the project's own page.
 *
 * Both registers already exist across every project; these are the same rows
 * cut to one project, so somebody looking after it sees what has come in and
 * what has gone out without leaving it (UX review 2026-10-05). Downloading an
 * export stays on the Exports register, where the staleness and hash checks
 * live - one place that does it carefully beats two that drift.
 */
"use client";

import { Upload } from "lucide-react";
import Link from "next/link";

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
} from "@/components/ui/primitives";
import { useCollections, useExports } from "@/features/exchange/queries";
import { formatDate, formatDateTime, humanise } from "@/lib/format";
import { withFrom } from "@/lib/navigation/return-to";
import type { Uuid } from "@/types";

export function ProjectCollectionsCard({
  projectUuid,
  from,
}: {
  projectUuid: Uuid;
  /** Where a collection opened from here comes back to. */
  from: string;
}) {
  const collections = useCollections(projectUuid);
  const items = collections.data?.items ?? [];

  return (
    <Card id="collections" className="scroll-mt-20">
      <CardHeader>
        <CardTitle>Collections</CardTitle>
      </CardHeader>
      {collections.isLoading ? (
        <CardBody>
          <Skeleton className="h-16" />
        </CardBody>
      ) : collections.error ? (
        <CardBody>
          <Alert tone="danger" title="Could not load this project's collections">
            {collections.error.userMessage()}
          </Alert>
        </CardBody>
      ) : items.length === 0 ? (
        <EmptyState
          title="No collections yet"
          description="A collection is recorded when a site's data source reports what it gathered under this project's consent."
        />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((c) => (
            <li key={c.collection_uuid}>
              <Link
                href={withFrom(`/collections/${c.collection_uuid}`, from)}
                className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-surface-hover"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{c.source_collection_ref}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    Collected {formatDate(c.collected_on)} · {c.source_name}
                    {c.site_label && ` · ${c.site_label}`}
                  </p>
                </div>
                {/* Declared against mapped is the figure that matters: a gap
                    is assets held with no consent behind them. */}
                <span
                  className={
                    c.mapped_asset_count < c.declared_asset_count
                      ? "tabular shrink-0 text-xs font-medium text-warning-text"
                      : "tabular shrink-0 text-xs text-text-muted"
                  }
                >
                  {c.mapped_asset_count} of {c.declared_asset_count} mapped
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ProjectExportsCard({
  projectUuid,
  canGenerate,
  onGenerate,
}: {
  projectUuid: Uuid;
  /** Only an approved project exports; the control is absent otherwise. */
  canGenerate: boolean;
  onGenerate: () => void;
}) {
  const exports = useExports(projectUuid);
  const items = exports.data ?? [];

  return (
    <Card id="exports" className="scroll-mt-20">
      <CardHeader className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>Exports</CardTitle>
        {canGenerate && (
          <Button variant="secondary" size="sm" onClick={onGenerate}>
            <Upload className="size-4" />
            Generate export
          </Button>
        )}
      </CardHeader>
      {exports.isLoading ? (
        <CardBody>
          <Skeleton className="h-16" />
        </CardBody>
      ) : exports.error ? (
        <CardBody>
          <Alert tone="danger" title="Could not load this project's exports">
            {exports.error.userMessage()}
          </Alert>
        </CardBody>
      ) : items.length === 0 ? (
        <EmptyState
          title="No exports yet"
          description={
            canGenerate
              ? "An export is the record of personal data leaving the platform for a site. Generate one when a site needs its consented list."
              : "Exports can be generated once the project is approved."
          }
        />
      ) : (
        <>
          <ul className="divide-y divide-border">
            {items.map((e) => (
              <li key={e.export_uuid} className="px-5 py-3">
                <p className="text-sm font-medium">
                  {humanise(e.export_type)}
                  <span className="ml-1.5 font-normal text-text-muted">
                    {e.site_label ?? "Whole project"}
                  </span>
                </p>
                <p className="mt-0.5 text-xs text-text-muted">
                  {formatDateTime(e.exported_at)} · {e.row_count}{" "}
                  {e.row_count === 1 ? "row" : "rows"}
                  {e.exported_by_name && ` · by ${e.exported_by_name}`}
                </p>
              </li>
            ))}
          </ul>
          <CardBody className="border-t border-border text-xs text-text-muted">
            Download them from the{" "}
            <Link href="/exports" className="font-medium text-accent-text hover:underline">
              Exports register
            </Link>
            , which checks each file against its recorded hash.
          </CardBody>
        </>
      )}
    </Card>
  );
}
