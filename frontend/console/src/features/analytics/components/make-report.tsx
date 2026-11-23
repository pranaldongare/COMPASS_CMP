/**
 * "Make this a report": what is on screen, as a file, made in the background
 * and kept in Reports. A format and a button; the server says whether the
 * role may have that kind.
 */
"use client";

import { FileDown } from "lucide-react";
import * as React from "react";

import { Button, Select } from "@/components/ui/primitives";
import { FORMAT_LABEL, errorText } from "@/features/analytics/format";
import { useCreateReport } from "@/features/analytics/mutations";
import { useToast } from "@/providers";
import type { Catalogue, ReportFormat, ReportInput } from "@/types";

export function MakeReport({
  catalogue,
  kind,
  params,
  label = "Make this a report",
  onMade,
}: {
  catalogue: Catalogue;
  kind: string;
  /** What the report is of: the period, the office, the audit report. */
  params: Omit<ReportInput, "kind" | "format">;
  label?: string;
  /** After it is queued: the page opens Reports, where it will appear. */
  onMade?: () => void;
}) {
  const info = catalogue.reports.find((r) => r.key === kind);
  const [format, setFormat] = React.useState<string>(info?.formats[0] ?? "pdf");
  const create = useCreateReport();
  const toast = useToast();
  const id = React.useId();
  if (!info) return null;

  async function make() {
    try {
      const made = await create.mutateAsync({
        kind,
        format: format as ReportFormat,
        ...params,
      });
      toast.success(
        "Report asked for",
        `${made.title} is being made. It will be ready in Reports.`,
      );
      onMade?.();
    } catch (err) {
      toast.error(
        "Could not make the report",
        errorText(err, "The report could not be asked for."),
      );
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label={label}>
      {info.formats.length > 1 && (
        <>
          <label htmlFor={id} className="sr-only">
            Format
          </label>
          <Select
            id={id}
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="h-9 w-auto"
          >
            {info.formats.map((f) => (
              <option key={f} value={f}>
                {FORMAT_LABEL[f] ?? f}
              </option>
            ))}
          </Select>
        </>
      )}
      <Button size="md" onClick={make} loading={create.isPending}>
        <FileDown className="size-4" aria-hidden="true" />
        {label}
        {info.formats.length === 1 &&
          ` (${FORMAT_LABEL[info.formats[0]] ?? info.formats[0]})`}
      </Button>
    </div>
  );
}
