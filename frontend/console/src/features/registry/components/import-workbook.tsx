/**
 * Processors or data sources from an Excel workbook (2026-10-14).
 *
 * The administrator's way to fill the registry: download the template (or the
 * sample), fill one row per record, check it, import it. The check writes
 * nothing and names every row in error by its spreadsheet row number. The
 * import is all or nothing - one row in error and nothing is created - and a
 * row already registered is skipped, so the same file can be sent again.
 */
"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Download, FileSpreadsheet, FileUp, Upload } from "lucide-react";
import * as React from "react";

import { FormError } from "@/components/forms";
import { Alert, Badge, Button, Table, Td, Th, Tr } from "@/components/ui/primitives";
import {
  applyRegistryImport,
  checkRegistryImport,
  registryImportTemplate,
} from "@/features/registry/api";
import { ApiError } from "@/lib/errors/api-error";
import { saveBlob } from "@/lib/format";
import { useToast } from "@/providers";
import type { RegistryImportKind, RegistryImportReport, RegistryImportRow } from "@/types";

const WORDS: Record<RegistryImportKind, { one: string; many: string; hint: string }> = {
  processors: {
    one: "processor",
    many: "processors",
    hint: "One row per lab, tool or partner: legal name, type, contract reference, the date its security was confirmed, whether it is in-house, and its country.",
  },
  sources: {
    one: "data source",
    many: "data sources",
    hint: "One row per source: code, name, role, exchange mode, and the processor that runs it by legal name or contract reference (blank for one we run ourselves). Import the processors first.",
  },
};

const OUTCOME: Record<RegistryImportRow["outcome"], { label: string; tone: "success" | "neutral" | "danger" | "accent" }> = {
  ready: { label: "Ready", tone: "accent" },
  created: { label: "Created", tone: "success" },
  skipped: { label: "Skipped", tone: "neutral" },
  error: { label: "Needs fixing", tone: "danger" },
};

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

/** A refused import carries its row report in the error body. */
function reportOf(err: unknown): RegistryImportReport | null {
  if (err instanceof ApiError && err.code === "import_rejected" && Array.isArray(err.details.rows)) {
    return err.details as unknown as RegistryImportReport;
  }
  return null;
}

function Counts({ report }: { report: RegistryImportReport }) {
  const rows: [string, number][] = [
    ["Rows read", report.total],
    [report.applied ? "Created" : "To be created", report.created],
    ["Already registered - skipped", report.skipped],
    ["Need fixing", report.errors],
  ];
  return (
    <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm">
      {rows.map(([label, n]) => (
        <React.Fragment key={label}>
          <dt className="text-text-muted">{label}</dt>
          <dd className="text-right font-medium tabular">{n}</dd>
        </React.Fragment>
      ))}
    </dl>
  );
}

function Rows({ report }: { report: RegistryImportReport }) {
  // The rows in error first: they are the ones to act on.
  const rows = [...report.rows].sort(
    (a, b) => Number(b.outcome === "error") - Number(a.outcome === "error") || a.row - b.row,
  );
  return (
    <div className="max-h-72 overflow-y-auto">
      <Table>
        <caption className="sr-only">Rows of the workbook</caption>
        <thead>
          <tr>
            <Th className="w-14">Row</Th>
            <Th>Name</Th>
            <Th className="w-32">Outcome</Th>
            <Th>Detail</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <Tr key={r.row}>
              <Td className="tabular text-text-muted">{r.row}</Td>
              <Td className="font-medium">{r.name ?? <span className="text-text-subtle">-</span>}</Td>
              <Td>
                <Badge tone={OUTCOME[r.outcome].tone}>{OUTCOME[r.outcome].label}</Badge>
              </Td>
              <Td className="text-xs">
                {r.problems.length > 0 ? (
                  <ul className="space-y-0.5 text-danger-text">
                    {r.problems.map((p) => (
                      <li key={`${p.column}:${p.message}`}>
                        <span className="font-medium">{p.column}:</span> {p.message}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-text-muted">{r.message ?? ""}</span>
                )}
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

/** Check a filled-in workbook, then import it. */
export function ImportWorkbook({
  kind,
  onDone,
}: {
  kind: RegistryImportKind;
  onDone: () => void;
}) {
  const toast = useToast();
  const qc = useQueryClient();
  const input = React.useRef<HTMLInputElement>(null);
  const [file, setFile] = React.useState<File | null>(null);
  const [report, setReport] = React.useState<RegistryImportReport | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<"template" | "sample" | "check" | "apply" | null>(null);
  const words = WORDS[kind];

  async function download(sample: boolean) {
    setBusy(sample ? "sample" : "template");
    try {
      const got = await registryImportTemplate(kind, sample);
      saveBlob(got.blob, got.filename);
    } catch (err) {
      toast.error("Could not download", messageOf(err, "The server refused."));
    } finally {
      setBusy(null);
    }
  }

  async function check() {
    if (!file) return;
    setBusy("check");
    setError(null);
    setReport(null);
    try {
      setReport(await checkRegistryImport(kind, file));
    } catch (err) {
      setError(messageOf(err, "The workbook could not be checked."));
    } finally {
      setBusy(null);
    }
  }

  async function apply() {
    if (!file) return;
    setBusy("apply");
    setError(null);
    try {
      const done = await applyRegistryImport(kind, file);
      const n = done.created;
      toast.success(
        `${n} ${n === 1 ? words.one : words.many} imported`,
        done.skipped ? `${done.skipped} already registered, skipped.` : undefined,
      );
      void qc.invalidateQueries({ queryKey: [kind] });
      onDone();
    } catch (err) {
      const refused = reportOf(err);
      if (refused) setReport(refused);
      setError(messageOf(err, "The workbook was not imported."));
    } finally {
      setBusy(null);
    }
  }

  const ready = report && !report.applied && report.errors === 0 ? report.created : 0;

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-muted">{words.hint}</p>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="sm" loading={busy === "template"} onClick={() => download(false)}>
          <Download className="size-4" />
          Download the template
        </Button>
        <Button variant="ghost" size="sm" loading={busy === "sample"} onClick={() => download(true)}>
          <FileSpreadsheet className="size-4" />
          Download sample data
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={input}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="sr-only"
          aria-label="The filled-in workbook"
          tabIndex={-1}
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setReport(null);
            setError(null);
          }}
        />
        <Button variant="secondary" size="sm" onClick={() => input.current?.click()}>
          <FileUp className="size-4" />
          {file ? "Choose another file" : "Choose the filled-in workbook"}
        </Button>
        {file && <span className="text-xs text-text-muted">{file.name}</span>}
      </div>
      <p className="text-xs text-text-subtle">
        An Excel workbook (.xlsx), up to 1,000 rows and 25 MB. Columns marked * are required.
      </p>

      <FormError message={error} />

      {report && (
        <div className="space-y-3 rounded-md bg-bg-inset p-3">
          <Counts report={report} />
          {report.errors > 0 ? (
            <Alert tone="warning">
              <p className="text-sm">
                Nothing is imported while any row needs fixing. Correct the rows below in the
                workbook and check it again.
              </p>
            </Alert>
          ) : (
            ready === 0 && (
              <Alert tone="info">
                <p className="text-sm">Every row is already registered: there is nothing to import.</p>
              </Alert>
            )
          )}
          <Rows report={report} />
        </div>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onDone}>
          Cancel
        </Button>
        <Button variant="secondary" size="sm" disabled={!file} loading={busy === "check"} onClick={check}>
          Check the workbook
        </Button>
        <Button variant="primary" size="sm" disabled={ready === 0} loading={busy === "apply"} onClick={apply}>
          <Upload className="size-4" />
          {ready > 0 ? `Import ${ready} ${ready === 1 ? words.one : words.many}` : "Import"}
        </Button>
      </div>
    </div>
  );
}
