/**
 * The administrator's: each figure's target and amber line, and the
 * small-number threshold below which a count of people is withheld.
 *
 * A target changes what every scorecard says, for everyone who reads it, so
 * an edit is one row at a time, the default is always one click away, and
 * who changed it last, and when, is in the row.
 */
"use client";

import { Pencil, RotateCcw } from "lucide-react";
import * as React from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { errorText, formatValue } from "@/features/analytics/format";
import {
  useResetTarget,
  useSetTarget,
  useSetThreshold,
} from "@/features/analytics/mutations";
import { useAnalyticsSettings } from "@/features/analytics/queries";
import { isApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { MetricTarget } from "@/types";

const UNIT: Record<string, string> = {
  count: "Count",
  percent: "Per cent",
  days: "Days",
  hours: "Hours",
};

function pair(target: number | null, amber: number | null, unit: string): string {
  if (target === null) return "—";
  return amber === null || amber === target
    ? formatValue(target, unit)
    : `${formatValue(target, unit)} · watch ${formatValue(amber, unit)}`;
}

export function SettingsPanel({ canWrite }: { canWrite: boolean }) {
  const settings = useAnalyticsSettings();
  const [editing, setEditing] = React.useState<string | null>(null);
  const reset = useResetTarget();
  const toast = useToast();

  if (settings.isLoading) return <Skeleton className="h-60" />;
  if (settings.isError) {
    return (
      <Alert tone="danger" title="Could not load the settings">
        {settings.error.userMessage()}
      </Alert>
    );
  }
  const data = settings.data!;

  async function backToDefault(t: MetricTarget) {
    try {
      await reset.mutateAsync(t.key);
      toast.success("Back to the default target", t.title);
    } catch (err) {
      toast.error("Could not change the target", errorText(err, "Try again in a moment."));
    }
  }

  return (
    <div className="space-y-6">
      <ThresholdCard
        value={data.small_number_threshold}
        updatedAt={data.updated_at}
        updatedBy={data.updated_by_name}
        canWrite={canWrite}
      />

      <Card>
        <CardHeader>
          <CardTitle>Targets</CardTitle>
          <p className="mt-0.5 text-xs text-text-muted">
            A figure is On target at its target, Watch between the target and the amber
            line, and Off target beyond it. Leave the amber line empty to have none.
          </p>
        </CardHeader>
        <Table aria-label="Targets">
          <thead>
            <tr>
              <Th>Figure</Th>
              <Th>Unit</Th>
              <Th>Default</Th>
              <Th>In force</Th>
              <Th>Changed</Th>
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {data.targets.map((t) =>
              editing === t.key ? (
                <TargetEditRow key={t.key} target={t} onDone={() => setEditing(null)} />
              ) : (
                <Tr key={t.key}>
                  <Td>
                    <p className="font-medium text-text">{t.title}</p>
                    <p className="text-xs text-text-subtle">
                      {t.group} ·{" "}
                      {t.higher_is_better ? "higher is better" : "lower is better"}
                    </p>
                  </Td>
                  <Td>{UNIT[t.unit] ?? t.unit}</Td>
                  <Td className="tabular whitespace-nowrap">
                    {pair(t.default_target, t.default_amber, t.unit)}
                  </Td>
                  <Td className="tabular whitespace-nowrap">
                    {pair(t.target, t.amber, t.unit)}
                    {t.customised && (
                      <Badge tone="accent" className="ml-2">
                        Customised
                      </Badge>
                    )}
                  </Td>
                  <Td className="text-xs text-text-muted">
                    {t.customised ? (
                      <>
                        {t.updated_by_name ?? "—"}
                        <br />
                        {formatDateTime(t.updated_at)}
                      </>
                    ) : (
                      "—"
                    )}
                  </Td>
                  <Td>
                    {canWrite && (
                      <div className="flex justify-end gap-1.5">
                        <Button
                          size="sm"
                          onClick={() => setEditing(t.key)}
                          aria-label={`Edit the target of ${t.title}`}
                        >
                          <Pencil className="size-4" aria-hidden="true" />
                          Edit
                        </Button>
                        {t.customised && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => backToDefault(t)}
                            aria-label={`Use the default target for ${t.title}`}
                          >
                            <RotateCcw className="size-4" aria-hidden="true" />
                            Use default
                          </Button>
                        )}
                      </div>
                    )}
                  </Td>
                </Tr>
              ),
            )}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}

function TargetEditRow({
  target: t,
  onDone,
}: {
  target: MetricTarget;
  onDone: () => void;
}) {
  const [target, setTarget] = React.useState(t.target === null ? "" : String(t.target));
  const [amber, setAmber] = React.useState(t.amber === null ? "" : String(t.amber));
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const save = useSetTarget();
  const toast = useToast();
  const unit = t.unit === "percent" ? "%" : t.unit === "count" ? "" : ` ${t.unit}`;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    const tv = Number(target);
    if (target.trim() === "" || Number.isNaN(tv) || tv < 0)
      local.target = "Give a target of nought or more.";
    const av = amber.trim() === "" ? null : Number(amber);
    if (av !== null && (Number.isNaN(av) || av < 0))
      local.amber = "Give an amber line of nought or more, or leave it empty.";
    setErrors(local);
    if (Object.keys(local).length) return;
    try {
      await save.mutateAsync({ key: t.key, input: { target: tv, amber: av } });
      toast.success("Target saved", t.title);
      onDone();
    } catch (err) {
      if (isApiError(err)) {
        const fields = err.fieldErrors();
        setErrors(Object.keys(fields).length ? fields : { target: err.userMessage() });
      } else setErrors({ target: "The target could not be saved." });
    }
  }

  return (
    <Tr>
      <Td colSpan={6}>
        <form
          method="post"
          onSubmit={submit}
          aria-label={`Target of ${t.title}`}
          className="space-y-3 py-1"
        >
          <p className="font-medium text-text">
            {t.title}{" "}
            <span className="text-xs font-normal text-text-subtle">
              (
              {t.higher_is_better
                ? "higher is better: amber sits below the target"
                : "lower is better: amber sits above the target"}
              )
            </span>
          </p>
          <div className="grid gap-3 sm:grid-cols-[12rem_12rem_auto] sm:items-start">
            <Field
              label={`Target${unit ? ` (${unit.trim()})` : ""}`}
              error={errors.target}
              required
            >
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  inputMode="decimal"
                  min={0}
                  step="any"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                />
              )}
            </Field>
            <Field
              label={`Amber line${unit ? ` (${unit.trim()})` : ""}`}
              error={errors.amber}
              hint={`Default ${pair(t.default_target, t.default_amber, t.unit)}`}
            >
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  inputMode="decimal"
                  min={0}
                  step="any"
                  value={amber}
                  onChange={(e) => setAmber(e.target.value)}
                />
              )}
            </Field>
            <div className="flex gap-2 sm:pt-6">
              <Button type="submit" variant="primary" size="md" loading={save.isPending}>
                Save
              </Button>
              <Button type="button" variant="ghost" onClick={onDone}>
                Cancel
              </Button>
            </div>
          </div>
        </form>
      </Td>
    </Tr>
  );
}

function ThresholdCard({
  value,
  updatedAt,
  updatedBy,
  canWrite,
}: {
  value: number;
  updatedAt: string | null;
  updatedBy: string | null;
  canWrite: boolean;
}) {
  const [draft, setDraft] = React.useState(String(value));
  const [error, setError] = React.useState<string | undefined>();
  const save = useSetThreshold();
  const toast = useToast();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const n = Number(draft);
    if (!Number.isInteger(n) || n < 1 || n > 100) {
      setError("Give a whole number from 1 to 100.");
      return;
    }
    setError(undefined);
    try {
      await save.mutateAsync(n);
      toast.success("Threshold saved", `Counts of fewer than ${n} people are withheld.`);
    } catch (err) {
      setError(
        isApiError(err)
          ? (err.fieldErrors().small_number_threshold ?? err.userMessage())
          : "The threshold could not be saved.",
      );
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Small-number threshold</CardTitle>
      </CardHeader>
      <CardBody>
        <p className="mb-4 max-w-2xl text-sm text-text-muted">
          A count of fewer people than this is withheld, everywhere a figure is shown or a
          report is made: it reads &ldquo;&lt; {value}&rdquo;, so nobody can be picked out
          of a small number. 1 withholds nothing.
          {updatedBy && (
            <>
              {" "}
              Last changed by {updatedBy}, {formatDateTime(updatedAt)}.
            </>
          )}
        </p>
        {canWrite ? (
          <form
            method="post"
            onSubmit={submit}
            className="flex flex-wrap items-start gap-3"
            aria-label="Small-number threshold"
          >
            <div className="w-40">
              <Field label="Threshold" error={error} hint="1 to 100 people">
                {(p) => (
                  <Input
                    {...p}
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={100}
                    step={1}
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                  />
                )}
              </Field>
            </div>
            <Button
              type="submit"
              variant="primary"
              className="mt-6"
              loading={save.isPending}
              disabled={draft === String(value)}
            >
              Save threshold
            </Button>
          </form>
        ) : (
          <p className="text-sm">
            Threshold: <span className="tabular font-semibold">{value}</span>
          </p>
        )}
      </CardBody>
    </Card>
  );
}
