/**
 * Logging an incident as it was noticed (S3-06: an incident first, a breach
 * on a yes).
 *
 * Every time here is typed in - never filled with "now". An incident logged
 * five hours after it was noticed has one hour of CERT-In time left, and the
 * register must show that rather than hide it; a field that defaulted to the
 * moment of saving would hide it.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Button, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { addBreachAttachment, recordBreach } from "@/features/breach/api";
import { AttachmentRows, type PendingAttachment } from "@/features/breach/components/attachments";
import { LOGGED_FIELDS, LoggedFields } from "@/features/breach/components/logged-details";
import { LOCATION_COPY } from "@/features/breach/components/copy";
import { useAllProcessors, useAllSources } from "@/features/registry/queries";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { BreachCyberAttack, BreachLocationKind, BreachLogged } from "@/types";

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

/** A to Z, ignoring case, and narrowed by what is typed. */
function arrange(options: { uuid: string; label: string; also?: string }[], q: string) {
  const term = q.trim().toLowerCase();
  return options
    .filter((o) => !term || `${o.label} ${o.also ?? ""}`.toLowerCase().includes(term))
    .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));
}

// Every row, not the newest fifty: an incident can be at any processor or
// source, however old, and the register's newest page left the seeded ones
// out (2026-10-06).
function useProcessorOptions(q: string) {
  const processors = useAllProcessors();
  return arrange(
    (processors.data ?? []).map((p) => ({ uuid: p.processor_uuid, label: p.legal_name, also: p.contract_ref })),
    q,
  );
}

function useSourceOptions(q: string) {
  const sources = useAllSources();
  return arrange(
    (sources.data ?? []).map((s) => ({ uuid: s.source_uuid, label: `${s.name} (${s.source_code})` })),
    q,
  );
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

/** Listed whole, A to Z, and narrowed by typing: the register can hold
 *  hundreds. */
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
  const [files, setFiles] = React.useState<PendingAttachment[]>([]);
  const [logged, setLogged] = React.useState<BreachLogged>({});
  const [cyber, setCyber] = React.useState<BreachCyberAttack | null>(null);
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
        ...Object.fromEntries(
          LOGGED_FIELDS.map((f) => [f.key, logged[f.key]?.trim() || null]),
        ),
        cyber_attack: cyber,
      });
      // The incident first - its clocks run from now - then its files, one by
      // one. A file the server refuses does not undo the incident: it is said,
      // and can be attached again from the incident's page.
      const chosen = files.filter((f): f is PendingAttachment & { file: File } => f.file !== null);
      const refused: string[] = [];
      for (const f of chosen) {
        try {
          await addBreachAttachment(made.breach_uuid, { file: f.file, kind: f.kind });
        } catch (err) {
          refused.push(`${f.file.name}: ${messageOf(err, "refused")}`);
        }
      }
      await qc.invalidateQueries({ queryKey: keys.breach.list() });
      toast.success(
        `${made.reference} logged`,
        chosen.length && !refused.length
          ? `With ${chosen.length} attached file${chosen.length === 1 ? "" : "s"}. Validate it next: is it a personal data breach?`
          : "Validate it next: is it a personal data breach?",
      );
      if (refused.length) {
        toast.error(
          `${refused.length} file${refused.length === 1 ? " was" : "s were"} not attached`,
          `${refused.join("; ")}. Attach ${refused.length === 1 ? "it" : "them"} from the incident's Attachments tab.`,
        );
      }
      onDone();
      router.push(`/breaches/${made.breach_uuid}${refused.length ? "#attachments" : ""}`);
    } catch (err) {
      toast.error("Not logged", messageOf(err, "The server refused."));
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
      <LoggedFields value={logged} onChange={setLogged} cyber={cyber} onCyber={setCyber} />
      <AttachmentRows rows={files} onChange={setFiles} />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={!ready} loading={record.isPending}>
          Log the incident
        </Button>
      </div>
    </form>
  );
}
