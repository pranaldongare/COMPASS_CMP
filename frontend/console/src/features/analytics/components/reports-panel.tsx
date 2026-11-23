/**
 * Reports made as files: the list, a new report, and the schedules that make
 * one on a cadence and mail it.
 *
 * A report is made in the background. Asking for one queues it (202); the
 * list then looks again every few seconds until it is ready or has failed,
 * so whoever asked sees it arrive without reloading. A file is downloaded
 * through the console's one download helper, and deleting one asks first -
 * the trail keeps that it was, the file is gone.
 */
"use client";

import { CalendarClock, Download, FilePlus2, Pause, Play, Trash2 } from "lucide-react";
import * as React from "react";

import { useConfirm } from "@/components/ui/confirm";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Field,
  Input,
  Select,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  FORMAT_LABEL,
  OFFICES,
  errorText,
  officeLabel,
  roleTitle,
} from "@/features/analytics/format";
import { downloadReport } from "@/features/analytics/api";
import {
  useCreateReport,
  useCreateSchedule,
  useDeleteReport,
  useDeleteSchedule,
  useSetScheduleActive,
} from "@/features/analytics/mutations";
import { useReports, useSchedules } from "@/features/analytics/queries";
import { isApiError } from "@/lib/errors";
import { formatBytes, formatDateTime, saveBlob } from "@/lib/format";
import { useToast } from "@/providers";
import type {
  Catalogue,
  OfficeCode,
  Report,
  ReportFormat,
  ReportInput,
  ReportKindInfo,
  ReportSchedule,
  ScheduleInput,
} from "@/types";

/** Kinds that are a snapshot or one case: they take no period. */
const NO_PERIOD = new Set(["data_inventory", "data_quality", "case_evidence"]);

const STATUS: Record<string, { label: string; tone: "info" | "success" | "danger" }> = {
  queued: { label: "Being made", tone: "info" },
  ready: { label: "Ready", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
};

export function ReportsPanel({
  catalogue,
  canWrite,
}: {
  catalogue: Catalogue;
  canWrite: boolean;
}) {
  const [making, setMaking] = React.useState(false);
  const [scheduling, setScheduling] = React.useState(false);
  const schedulable = catalogue.reports.filter((r) => r.schedulable);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>Reports</CardTitle>
          {canWrite && catalogue.reports.length > 0 && !making && (
            <Button size="sm" variant="primary" onClick={() => setMaking(true)}>
              <FilePlus2 className="size-4" aria-hidden="true" />
              New report
            </Button>
          )}
        </CardHeader>
        {making && (
          <CardBody className="border-b border-border">
            <NewReportForm catalogue={catalogue} onDone={() => setMaking(false)} />
          </CardBody>
        )}
        <ReportList catalogue={catalogue} canWrite={canWrite} />
      </Card>

      {schedulable.length > 0 && (
        <Card>
          <CardHeader className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Schedules</CardTitle>
              <p className="mt-0.5 text-xs text-text-muted">
                A report made on a cadence and mailed to the roles chosen.
              </p>
            </div>
            {canWrite && !scheduling && (
              <Button size="sm" onClick={() => setScheduling(true)}>
                <CalendarClock className="size-4" aria-hidden="true" />
                New schedule
              </Button>
            )}
          </CardHeader>
          {scheduling && (
            <CardBody className="border-b border-border">
              <NewScheduleForm
                catalogue={catalogue}
                kinds={schedulable}
                onDone={() => setScheduling(false)}
              />
            </CardBody>
          )}
          <ScheduleList catalogue={catalogue} canWrite={canWrite} />
        </Card>
      )}
    </div>
  );
}

/* =================================================================== list */

function ReportList({ catalogue, canWrite }: { catalogue: Catalogue; canWrite: boolean }) {
  const reports = useReports();
  const remove = useDeleteReport();
  const toast = useToast();
  const { ask, dialog } = useConfirm();
  const [busy, setBusy] = React.useState<string | null>(null);
  const kindTitle = (k: string) => catalogue.reports.find((r) => r.key === k)?.title ?? k;

  async function download(r: Report) {
    setBusy(r.report_uuid);
    try {
      const file = await downloadReport(r.report_uuid);
      saveBlob(file.blob, file.filename);
      toast.success("Downloaded", file.filename);
    } catch (err) {
      toast.error(
        "Could not download the report",
        errorText(err, "Try again in a moment."),
      );
    } finally {
      setBusy(null);
    }
  }

  async function drop(r: Report) {
    const yes = await ask({
      title: "Delete this report?",
      consequence: (
        <>
          <strong>{r.title}</strong> and its file are deleted for everybody who could read
          it. The audit trail keeps that it was made and deleted.
        </>
      ),
      confirmLabel: "Delete report",
      tone: "danger",
    });
    if (!yes) return;
    try {
      await remove.mutateAsync(r.report_uuid);
      toast.success("Report deleted");
    } catch (err) {
      toast.error("Could not delete the report", errorText(err, "Try again in a moment."));
    }
  }

  if (reports.isLoading)
    return (
      <CardBody>
        <Skeleton className="h-32" />
      </CardBody>
    );
  if (reports.isError) {
    return (
      <CardBody>
        <Alert tone="danger" title="Could not load the reports">
          {reports.error.userMessage()}
        </Alert>
      </CardBody>
    );
  }
  const rows = reports.data ?? [];
  if (rows.length === 0) {
    return (
      <EmptyState
        title="No reports yet"
        description="A report you ask for, or one a schedule makes, is kept here to download."
      />
    );
  }
  return (
    <>
      <Table aria-label="Reports">
        <thead>
          <tr>
            <Th>Report</Th>
            <Th>Format</Th>
            <Th>Status</Th>
            <Th>Asked for by</Th>
            <Th>Made</Th>
            <Th className="text-right">Size</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const s = STATUS[r.status] ?? { label: r.status, tone: "info" as const };
            return (
              <Tr key={r.report_uuid}>
                <Td>
                  <p className="font-medium text-text">{r.title}</p>
                  <p className="text-xs text-text-subtle">
                    {kindTitle(r.kind)}
                    {r.office && <> · {officeLabel(r.office)}</>}
                  </p>
                </Td>
                <Td>{FORMAT_LABEL[r.format] ?? r.format}</Td>
                <Td>
                  <Badge tone={s.tone} dot>
                    {s.label}
                  </Badge>
                  {r.status === "failed" && r.error && (
                    <p className="mt-1 max-w-56 text-xs text-danger-text">{r.error}</p>
                  )}
                </Td>
                <Td>
                  {r.schedule_uuid ? (
                    <span className="inline-flex items-center gap-1 text-text-muted">
                      <CalendarClock className="size-3.5" aria-hidden="true" />A schedule
                    </span>
                  ) : (
                    <>
                      <p>{r.requested_by_name ?? "—"}</p>
                      <p className="text-xs text-text-subtle">
                        {roleTitle(r.requested_role)}
                      </p>
                    </>
                  )}
                </Td>
                <Td className="whitespace-nowrap">{formatDateTime(r.created_at)}</Td>
                <Td className="tabular text-right whitespace-nowrap">
                  {r.file_bytes !== null ? formatBytes(r.file_bytes) : "—"}
                </Td>
                <Td>
                  <div className="flex justify-end gap-1.5">
                    {r.status === "ready" && (
                      <Button
                        size="sm"
                        onClick={() => download(r)}
                        loading={busy === r.report_uuid}
                        aria-label={`Download ${r.title}`}
                      >
                        <Download className="size-4" aria-hidden="true" />
                        Download
                      </Button>
                    )}
                    {canWrite && (
                      <Button
                        size="sm"
                        variant="subtle"
                        onClick={() => drop(r)}
                        aria-label={`Delete ${r.title}`}
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                        Delete
                      </Button>
                    )}
                  </div>
                </Td>
              </Tr>
            );
          })}
        </tbody>
      </Table>
      {dialog}
    </>
  );
}

/* ============================================================= new report */

function useFieldErrors() {
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [general, setGeneral] = React.useState<string | null>(null);
  return {
    errors,
    general,
    clear: () => {
      setErrors({});
      setGeneral(null);
    },
    take: (err: unknown, fallback: string) => {
      if (isApiError(err)) {
        const fields = err.fieldErrors();
        setErrors(fields);
        setGeneral(Object.keys(fields).length ? null : err.userMessage());
      } else setGeneral(fallback);
    },
  };
}

function NewReportForm({
  catalogue,
  onDone,
}: {
  catalogue: Catalogue;
  onDone: () => void;
}) {
  const kinds = catalogue.reports;
  const [kind, setKind] = React.useState(kinds[0]?.key ?? "");
  const info = kinds.find((k) => k.key === kind);
  const [format, setFormat] = React.useState(info?.formats[0] ?? "pdf");
  const [period, setPeriod] = React.useState("last_month");
  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");
  const [office, setOffice] = React.useState("");
  const [audit, setAudit] = React.useState(catalogue.audit_reports[0]?.key ?? "");
  const [entityType, setEntityType] = React.useState<"rights_request" | "breach">(
    "rights_request",
  );
  const [entityUuid, setEntityUuid] = React.useState("");
  const create = useCreateReport();
  const toast = useToast();
  const fe = useFieldErrors();

  const takesPeriod = !NO_PERIOD.has(kind);

  function chooseKind(next: string) {
    setKind(next);
    const formats = kinds.find((k) => k.key === next)?.formats ?? [];
    if (!formats.includes(format)) setFormat(formats[0] ?? "pdf");
    fe.clear();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    fe.clear();
    const input: ReportInput = { kind, format: format as ReportFormat };
    if (takesPeriod) {
      input.period = period;
      if (period === "custom") {
        input.start = start || null;
        input.end = end || null;
      }
    }
    if (catalogue.may_choose_office && office) input.office = office as OfficeCode;
    if (kind === "audit") input.audit = audit;
    if (kind === "case_evidence") {
      input.entity_type = entityType;
      input.entity_uuid = entityUuid.trim();
    }
    try {
      const made = await create.mutateAsync(input);
      toast.success(
        "Report asked for",
        `${made.title} is being made. It will appear below when ready.`,
      );
      onDone();
    } catch (err) {
      fe.take(err, "The report could not be asked for.");
    }
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-4" aria-label="New report">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Report" error={fe.errors.kind} hint={info?.description}>
          {(p) => (
            <Select {...p} value={kind} onChange={(e) => chooseKind(e.target.value)}>
              {kinds.map((k) => (
                <option key={k.key} value={k.key}>
                  {k.title}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Format" error={fe.errors.format}>
          {(p) => (
            <Select {...p} value={format} onChange={(e) => setFormat(e.target.value)}>
              {(info?.formats ?? []).map((f) => (
                <option key={f} value={f}>
                  {FORMAT_LABEL[f] ?? f}
                </option>
              ))}
            </Select>
          )}
        </Field>
        {takesPeriod && (
          <Field label="Period" error={fe.errors.period}>
            {(p) => (
              <Select {...p} value={period} onChange={(e) => setPeriod(e.target.value)}>
                {catalogue.periods.map((o) => (
                  <option key={o.key} value={o.key}>
                    {o.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
        {takesPeriod && period === "custom" && (
          <>
            <Field label="First day" error={fe.errors.start} required>
              {(p) => (
                <Input
                  {...p}
                  type="date"
                  value={start}
                  max={end || undefined}
                  onChange={(e) => setStart(e.target.value)}
                />
              )}
            </Field>
            <Field label="Last day" error={fe.errors.end} required>
              {(p) => (
                <Input
                  {...p}
                  type="date"
                  value={end}
                  min={start || undefined}
                  onChange={(e) => setEnd(e.target.value)}
                />
              )}
            </Field>
          </>
        )}
        {catalogue.may_choose_office && kind !== "case_evidence" && (
          <Field label="Office" error={fe.errors.office}>
            {(p) => (
              <Select {...p} value={office} onChange={(e) => setOffice(e.target.value)}>
                <option value="">All offices</option>
                {OFFICES.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
        {kind === "audit" && (
          <Field label="Audit report" error={fe.errors.audit}>
            {(p) => (
              <Select {...p} value={audit} onChange={(e) => setAudit(e.target.value)}>
                {catalogue.audit_reports.map((a) => (
                  <option key={a.key} value={a.key}>
                    {a.title}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
        {kind === "case_evidence" && (
          <>
            <Field label="Case" error={fe.errors.entity_type}>
              {(p) => (
                <Select
                  {...p}
                  value={entityType}
                  onChange={(e) =>
                    setEntityType(e.target.value as "rights_request" | "breach")
                  }
                >
                  <option value="rights_request">A rights request</option>
                  <option value="breach">A breach</option>
                </Select>
              )}
            </Field>
            <Field
              label="Its reference (UUID)"
              error={fe.errors.entity_uuid}
              hint="From the address of the request's or breach's page."
              required
            >
              {(p) => (
                <Input
                  {...p}
                  value={entityUuid}
                  onChange={(e) => setEntityUuid(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  autoComplete="off"
                  spellCheck={false}
                />
              )}
            </Field>
          </>
        )}
      </div>
      {fe.general && <Alert tone="danger">{fe.general}</Alert>}
      <div className="flex gap-2">
        <Button type="submit" variant="primary" loading={create.isPending}>
          Make report
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

/* ============================================================== schedules */

function ScheduleList({
  catalogue,
  canWrite,
}: {
  catalogue: Catalogue;
  canWrite: boolean;
}) {
  const schedules = useSchedules();
  const setActive = useSetScheduleActive();
  const remove = useDeleteSchedule();
  const toast = useToast();
  const { ask, dialog } = useConfirm();
  const cadence = (c: string) => catalogue.cadences.find((x) => x.key === c)?.label ?? c;

  async function toggle(s: ReportSchedule) {
    try {
      await setActive.mutateAsync({ uuid: s.schedule_uuid, active: !s.active });
      toast.success(s.active ? "Schedule paused" : "Schedule resumed", s.title);
    } catch (err) {
      toast.error(
        "Could not change the schedule",
        errorText(err, "Try again in a moment."),
      );
    }
  }

  async function drop(s: ReportSchedule) {
    const yes = await ask({
      title: "Remove this schedule?",
      consequence: (
        <>
          <strong>{s.title}</strong> will no longer be made or mailed. Reports it has
          already made are kept.
        </>
      ),
      confirmLabel: "Remove schedule",
      tone: "danger",
    });
    if (!yes) return;
    try {
      await remove.mutateAsync(s.schedule_uuid);
      toast.success("Schedule removed");
    } catch (err) {
      toast.error(
        "Could not remove the schedule",
        errorText(err, "Try again in a moment."),
      );
    }
  }

  if (schedules.isLoading)
    return (
      <CardBody>
        <Skeleton className="h-24" />
      </CardBody>
    );
  if (schedules.isError) {
    return (
      <CardBody>
        <Alert tone="danger" title="Could not load the schedules">
          {schedules.error.userMessage()}
        </Alert>
      </CardBody>
    );
  }
  const rows = schedules.data ?? [];
  if (rows.length === 0) {
    return (
      <CardBody className="text-sm text-text-muted">
        No report is made on a schedule yet.
      </CardBody>
    );
  }
  return (
    <>
      <Table aria-label="Schedules">
        <thead>
          <tr>
            <Th>Report</Th>
            <Th>When</Th>
            <Th>Mailed to</Th>
            <Th>Status</Th>
            <Th>Next</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <Tr key={s.schedule_uuid}>
              <Td>
                <p className="font-medium text-text">{s.title}</p>
                <p className="text-xs text-text-subtle">
                  {FORMAT_LABEL[s.format] ?? s.format}
                  {s.office && <> · {officeLabel(s.office)}</>}
                  {s.created_by_name && <> · set up by {s.created_by_name}</>}
                </p>
              </Td>
              <Td>{cadence(s.cadence)}</Td>
              <Td>{s.recipient_roles.map(roleTitle).join(", ")}</Td>
              <Td>
                <Badge tone={s.active ? "success" : "neutral"} dot>
                  {s.active ? "Active" : "Paused"}
                </Badge>
              </Td>
              <Td className="whitespace-nowrap">
                {s.active ? formatDateTime(s.next_run_at) : "—"}
                {s.last_run_at && (
                  <p className="text-xs text-text-subtle">
                    Last {formatDateTime(s.last_run_at)}
                  </p>
                )}
              </Td>
              <Td>
                {canWrite && (
                  <div className="flex justify-end gap-1.5">
                    <Button
                      size="sm"
                      onClick={() => toggle(s)}
                      aria-label={`${s.active ? "Pause" : "Resume"} ${s.title}`}
                    >
                      {s.active ? (
                        <Pause className="size-4" aria-hidden="true" />
                      ) : (
                        <Play className="size-4" aria-hidden="true" />
                      )}
                      {s.active ? "Pause" : "Resume"}
                    </Button>
                    <Button
                      size="sm"
                      variant="subtle"
                      onClick={() => drop(s)}
                      aria-label={`Remove ${s.title}`}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                      Remove
                    </Button>
                  </div>
                )}
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
      {dialog}
    </>
  );
}

function NewScheduleForm({
  catalogue,
  kinds,
  onDone,
}: {
  catalogue: Catalogue;
  kinds: ReportKindInfo[];
  onDone: () => void;
}) {
  const [kind, setKind] = React.useState(kinds[0]?.key ?? "");
  const info = kinds.find((k) => k.key === kind);
  const [format, setFormat] = React.useState(info?.formats[0] ?? "pdf");
  const [cadence, setCadence] = React.useState(
    catalogue.cadences[1]?.key ?? catalogue.cadences[0]?.key ?? "monthly",
  );
  const [roles, setRoles] = React.useState<string[]>([]);
  const [office, setOffice] = React.useState("");
  const [audit, setAudit] = React.useState(catalogue.audit_reports[0]?.key ?? "");
  const create = useCreateSchedule();
  const toast = useToast();
  const fe = useFieldErrors();
  const groupId = React.useId();

  function chooseKind(next: string) {
    setKind(next);
    const k = kinds.find((x) => x.key === next);
    if (k && !k.formats.includes(format)) setFormat(k.formats[0] ?? "pdf");
    setRoles((r) => r.filter((x) => k?.recipient_roles.includes(x)));
    fe.clear();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    fe.clear();
    const input: ScheduleInput = {
      kind,
      format: format as ReportFormat,
      cadence: cadence as ScheduleInput["cadence"],
      recipient_roles: roles,
    };
    if (catalogue.may_choose_office && office) input.office = office as OfficeCode;
    if (kind === "audit") input.audit = audit;
    try {
      const made = await create.mutateAsync(input);
      toast.success("Schedule set up", made.title);
      onDone();
    } catch (err) {
      fe.take(err, "The schedule could not be set up.");
    }
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-4" aria-label="New schedule">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Report" error={fe.errors.kind} hint={info?.description}>
          {(p) => (
            <Select {...p} value={kind} onChange={(e) => chooseKind(e.target.value)}>
              {kinds.map((k) => (
                <option key={k.key} value={k.key}>
                  {k.title}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Format" error={fe.errors.format}>
          {(p) => (
            <Select {...p} value={format} onChange={(e) => setFormat(e.target.value)}>
              {(info?.formats ?? []).map((f) => (
                <option key={f} value={f}>
                  {FORMAT_LABEL[f] ?? f}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="How often" error={fe.errors.cadence}>
          {(p) => (
            <Select {...p} value={cadence} onChange={(e) => setCadence(e.target.value)}>
              {catalogue.cadences.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
        {catalogue.may_choose_office && (
          <Field label="Office" error={fe.errors.office}>
            {(p) => (
              <Select {...p} value={office} onChange={(e) => setOffice(e.target.value)}>
                <option value="">All offices</option>
                {OFFICES.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
        {kind === "audit" && (
          <Field label="Audit report" error={fe.errors.audit}>
            {(p) => (
              <Select {...p} value={audit} onChange={(e) => setAudit(e.target.value)}>
                {catalogue.audit_reports.map((a) => (
                  <option key={a.key} value={a.key}>
                    {a.title}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        )}
      </div>
      <fieldset aria-describedby={fe.errors.recipient_roles ? `${groupId}-err` : undefined}>
        <legend className="text-sm font-medium text-text">Mail it to</legend>
        <p className="mt-0.5 text-xs text-text-subtle">
          Everyone active in the roles chosen
          {catalogue.may_choose_office ? "" : ", in your office"}.
        </p>
        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
          {(info?.recipient_roles ?? []).map((r) => (
            <label
              key={r}
              className="inline-flex cursor-pointer items-center gap-2 text-sm"
            >
              <input
                type="checkbox"
                checked={roles.includes(r)}
                onChange={(e) =>
                  setRoles((cur) =>
                    e.target.checked ? [...cur, r] : cur.filter((x) => x !== r),
                  )
                }
                className="size-4 rounded border-border-strong accent-[var(--accent)]"
              />
              {roleTitle(r)}
            </label>
          ))}
        </div>
        {fe.errors.recipient_roles && (
          <p id={`${groupId}-err`} role="alert" className="mt-1 text-xs text-danger-text">
            {fe.errors.recipient_roles}
          </p>
        )}
      </fieldset>
      {fe.general && <Alert tone="danger">{fe.general}</Alert>}
      <div className="flex gap-2">
        <Button
          type="submit"
          variant="primary"
          loading={create.isPending}
          disabled={roles.length === 0}
        >
          Set up schedule
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
