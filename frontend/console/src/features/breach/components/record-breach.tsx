/**
 * Recording a breach as it was noticed.
 *
 * Every time here is typed in - never filled with "now". A breach recorded
 * five hours after it was noticed has one hour of CERT-In time left, and the
 * register must show that rather than hide it; a field that defaulted to the
 * moment of saving would hide it.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Button, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { recordBreach } from "@/features/breach/api";
import { LOCATION_COPY } from "@/features/breach/components/copy";
import { useProcessors, useSources } from "@/features/registry/queries";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { BreachLocationKind } from "@/types";

/** A `datetime-local` value as an instant, or null when empty. */
export function instant(local: string): string | null {
  if (!local) return null;
  const at = new Date(local);
  return Number.isNaN(at.getTime()) ? null : at.toISOString();
}

export function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

function useProcessorOptions(q: string) {
  const filters = { q: q || undefined, limit: 50 };
  const processors = useProcessors(filters);
  return (processors.data?.items ?? []).map((p) => ({ uuid: p.processor_uuid, label: p.legal_name }));
}

function useSourceOptions(q: string) {
  const sources = useSources({ q: q || undefined, limit: 50 });
  return (sources.data?.items ?? []).map((s) => ({
    uuid: s.source_uuid,
    label: `${s.name} (${s.source_code})`,
  }));
}

function Choose({
  label,
  q,
  setQ,
  options,
  value,
  onChange,
}: {
  label: string;
  q: string;
  setQ: (q: string) => void;
  options: { uuid: string; label: string }[];
  value: string;
  onChange: (uuid: string) => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <Field label={`Find the ${label.toLowerCase()}`} hint="Name or code">
        {(p) => <Input {...p} value={q} onChange={(e) => setQ(e.target.value)} />}
      </Field>
      <Field label={label} required>
        {(p) => (
          <Select {...p} value={value} onChange={(e) => onChange(e.target.value)}>
            <option value="">Choose…</option>
            {options.map((o) => (
              <option key={o.uuid} value={o.uuid}>
                {o.label}
              </option>
            ))}
          </Select>
        )}
      </Field>
    </div>
  );
}

/** Searched rather than listed whole: the register can hold hundreds. */
export function ProcessorPicker({ value, onChange }: { value: string; onChange: (uuid: string) => void }) {
  const [q, setQ] = React.useState("");
  const options = useProcessorOptions(q);
  return <Choose label="Processor" q={q} setQ={setQ} options={options} value={value} onChange={onChange} />;
}

export function SourcePicker({ value, onChange }: { value: string; onChange: (uuid: string) => void }) {
  const [q, setQ] = React.useState("");
  const options = useSourceOptions(q);
  return <Choose label="Data source" q={q} setQ={setQ} options={options} value={value} onChange={onChange} />;
}

export function RecordBreachForm({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const router = useRouter();
  const [title, setTitle] = React.useState("");
  const [detected, setDetected] = React.useState("");
  const [began, setBegan] = React.useState("");
  const [kind, setKind] = React.useState<BreachLocationKind>("platform");
  const [target, setTarget] = React.useState("");
  const [detail, setDetail] = React.useState("");
  const record = useMutation({ mutationFn: recordBreach });

  const detectedAt = instant(detected);
  const ready =
    title.trim() !== "" &&
    detectedAt !== null &&
    (kind === "platform" || kind === "other" ? true : target !== "") &&
    (kind !== "other" || detail.trim() !== "");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready || !detectedAt) return;
    try {
      const made = await record.mutateAsync({
        title: title.trim(),
        detected_at: detectedAt,
        began_at: instant(began),
        location_kind: kind,
        processor_uuid: kind === "processor" ? target : null,
        source_uuid: kind === "data_source" ? target : null,
        location_detail: detail.trim() || null,
      });
      await qc.invalidateQueries({ queryKey: keys.breach.list() });
      toast.success(`${made.reference} recorded`, "Record the determination next.");
      onDone();
      router.push(`/breaches/${made.breach_uuid}`);
    } catch (err) {
      toast.error("Not recorded", messageOf(err, "The server refused."));
    }
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-4">
      <Field label="Title" hint="A few words the office will know it by" required>
        {(p) => <Input {...p} value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} />}
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="First noticed" hint="When it was detected. Starts the CERT-In clock" required>
          {(p) => (
            <Input {...p} type="datetime-local" value={detected} onChange={(e) => setDetected(e.target.value)} />
          )}
        </Field>
        <Field label="Began" hint="If known. An assessment can revise it">
          {(p) => <Input {...p} type="datetime-local" value={began} onChange={(e) => setBegan(e.target.value)} />}
        </Field>
      </div>
      <Field label="Where it occurred" required>
        {(p) => (
          <Select
            {...p}
            value={kind}
            onChange={(e) => {
              setKind(e.target.value as BreachLocationKind);
              setTarget("");
            }}
          >
            {(Object.keys(LOCATION_COPY) as BreachLocationKind[]).map((k) => (
              <option key={k} value={k}>
                {LOCATION_COPY[k]}
              </option>
            ))}
          </Select>
        )}
      </Field>
      {kind === "processor" && <ProcessorPicker value={target} onChange={setTarget} />}
      {kind === "data_source" && <SourcePicker value={target} onChange={setTarget} />}
      <Field
        label="Where, in words"
        hint={kind === "other" ? "Which store or system" : "Optional: the system, the table, the device"}
        required={kind === "other"}
      >
        {(p) => <Textarea {...p} value={detail} onChange={(e) => setDetail(e.target.value)} />}
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={!ready} loading={record.isPending}>
          Record the breach
        </Button>
      </div>
    </form>
  );
}
