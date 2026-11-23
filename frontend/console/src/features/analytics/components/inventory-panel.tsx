/**
 * The record of processing: every purpose with what it covers, its lawful
 * basis and retention; every processor with its country; every data source.
 * As the registers have them today - a snapshot, whatever the period.
 */
"use client";

import * as React from "react";

import {
  Alert,
  Card,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { MakeReport } from "@/features/analytics/components/make-report";
import { officeLabel } from "@/features/analytics/format";
import { useInventory } from "@/features/analytics/queries";
import { formatDate, humanise } from "@/lib/format";
import type { Catalogue } from "@/types";

interface Column {
  key: string;
  label: string;
  kind?: "enum" | "bool" | "date" | "list" | "office";
}

const PURPOSES: Column[] = [
  { key: "purpose_code", label: "Code" },
  { key: "name", label: "Purpose" },
  { key: "office", label: "Office", kind: "office" },
  { key: "status", label: "Status", kind: "enum" },
  { key: "lawful_basis", label: "Lawful basis", kind: "enum" },
  { key: "data_categories", label: "Data categories", kind: "list" },
  { key: "retention_period", label: "Retention" },
  { key: "retention_basis", label: "Retention basis", kind: "enum" },
  { key: "consent_validity_period", label: "Consent valid for" },
  { key: "cross_border_permitted", label: "Outside India", kind: "bool" },
  { key: "permitted_for_minors", label: "Children", kind: "bool" },
];

const PROCESSORS: Column[] = [
  { key: "legal_name", label: "Processor" },
  { key: "type", label: "Type", kind: "enum" },
  { key: "status", label: "Status", kind: "enum" },
  { key: "is_in_house", label: "In-house", kind: "bool" },
  { key: "location_country", label: "Country" },
  { key: "security_confirmed_at", label: "Security confirmed", kind: "date" },
  { key: "contract_ref", label: "Contract" },
];

const SOURCES: Column[] = [
  { key: "source_code", label: "Code" },
  { key: "name", label: "Source" },
  { key: "status", label: "Status", kind: "enum" },
  { key: "source_role", label: "Role", kind: "enum" },
  { key: "exchange_mode", label: "Exchange", kind: "enum" },
  { key: "processor", label: "Processor" },
];

function cell(value: unknown, kind: Column["kind"]): string {
  if (value === null || value === undefined || value === "") return "—";
  if (kind === "bool") return value ? "Yes" : "No";
  if (kind === "date") return formatDate(String(value));
  if (kind === "office") return officeLabel(String(value));
  if (Array.isArray(value))
    return value.length ? value.map((v) => humanise(String(v))).join(", ") : "—";
  if (kind === "enum") return humanise(String(value));
  return String(value);
}

function Register({
  title,
  columns,
  rows,
}: {
  title: string;
  columns: Column[];
  rows: Record<string, unknown>[];
}) {
  const id = React.useId();
  return (
    <Card>
      <CardHeader>
        <CardTitle id={id}>
          {title}{" "}
          <span className="tabular font-normal text-text-muted">({rows.length})</span>
        </CardTitle>
      </CardHeader>
      {rows.length === 0 ? (
        <EmptyState title={`No ${title.toLowerCase()} recorded`} />
      ) : (
        <Table aria-labelledby={id}>
          <thead>
            <tr>
              {columns.map((c) => (
                <Th key={c.key} className="whitespace-nowrap">
                  {c.label}
                </Th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <Tr key={i}>
                {columns.map((c) => (
                  <Td key={c.key}>{cell(row[c.key], c.kind)}</Td>
                ))}
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

export function InventoryPanel({
  catalogue,
  office,
  onMade,
}: {
  catalogue: Catalogue;
  office: string | undefined;
  onMade: () => void;
}) {
  const query = useInventory(office);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-3xl text-sm text-text-muted">
          What the organisation processes, for what, on what basis and for how long, by whom
          and where: the registers as they stand today.
          {catalogue.may_choose_office && <> Purposes shown: {officeLabel(office)}.</>}
        </p>
        <MakeReport
          catalogue={catalogue}
          kind="data_inventory"
          params={{ office: (office as "rnd" | "hr" | undefined) ?? null }}
          label="Make the record a report"
          onMade={onMade}
        />
      </div>
      {query.isLoading ? (
        <Skeleton className="h-60" />
      ) : query.isError ? (
        <Alert tone="danger" title="Could not read the record of processing">
          {query.error.userMessage()}
        </Alert>
      ) : query.data ? (
        <>
          <Register title="Purposes" columns={PURPOSES} rows={query.data.purposes} />
          <Register title="Processors" columns={PROCESSORS} rows={query.data.processors} />
          <Register title="Data sources" columns={SOURCES} rows={query.data.sources} />
        </>
      ) : null}
    </div>
  );
}
