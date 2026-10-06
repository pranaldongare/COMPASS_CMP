/**
 * Files kept with an incident: the email that reported it, a proof, a chat
 * (2026-10-06).
 *
 * Evidence, kept as it came: never replaced or removed, so there is no
 * delete here - a file added in error stays, with the right one beside it.
 * Every download is on the trail. The name and the note are sealed, opened
 * by the API client like every other personal field.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Paperclip, Plus, X } from "lucide-react";
import * as React from "react";

import { FileInput } from "@/components/forms";
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
  Select,
} from "@/components/ui/primitives";
import { addBreachAttachment, breachAttachmentUrl } from "@/features/breach/api";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { Breach, BreachAttachmentKind } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export const ATTACHMENT_KIND: Record<BreachAttachmentKind, string> = {
  email: "Email",
  proof: "Proof",
  chat: "Chat",
  other: "Other",
};

/** What the API takes: documents, images, saved emails, text - nothing
 *  that runs. 25 MB each. */
export const ATTACHMENT_ACCEPT = ".pdf,.png,.jpg,.jpeg,.txt,.csv,.log,.eml,.msg,.docx";
export const ATTACHMENT_MAX_BYTES = 25 * 1024 * 1024;

export interface PendingAttachment {
  key: number;
  file: File | null;
  kind: BreachAttachmentKind;
}

/** Files chosen before the incident exists: sent once it is logged. */
export function AttachmentRows({
  rows,
  onChange,
}: {
  rows: PendingAttachment[];
  onChange: (rows: PendingAttachment[]) => void;
}) {
  const nextKey = React.useRef(rows.length);
  const update = (key: number, change: Partial<PendingAttachment>) =>
    onChange(rows.map((r) => (r.key === key ? { ...r, ...change } : r)));
  return (
    <fieldset className="space-y-2">
      <legend className="mb-1 text-sm font-medium">Attachments</legend>
      <p className="text-xs text-text-muted">
        Optional: the email that reported it, a screenshot, a chat or a log - kept with the incident as evidence. PDF,
        images, text, saved emails (.eml, .msg) or Word; 25 MB each.
      </p>
      {rows.map((r, i) => (
        <div key={r.key} className="grid items-end gap-2 sm:grid-cols-[1fr_9rem_auto]">
          <FileInput
            label={`File ${i + 1}`}
            accept={ATTACHMENT_ACCEPT}
            maxBytes={ATTACHMENT_MAX_BYTES}
            file={r.file}
            onChange={(file) => update(r.key, { file })}
          />
          <Field label="What it is">
            {(p) => (
              <Select
                {...p}
                value={r.kind}
                onChange={(e) => update(r.key, { kind: e.target.value as BreachAttachmentKind })}
              >
                {(Object.keys(ATTACHMENT_KIND) as BreachAttachmentKind[]).map((k) => (
                  <option key={k} value={k}>
                    {ATTACHMENT_KIND[k]}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-label={`Remove file ${i + 1}`}
            onClick={() => onChange(rows.filter((x) => x.key !== r.key))}
          >
            <X className="size-4" />
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={() => {
          nextKey.current += 1;
          onChange([...rows, { key: nextKey.current, file: null, kind: rows.length ? "proof" : "email" }]);
        }}
      >
        <Paperclip className="size-4" />
        {rows.length ? "Attach another file" : "Attach a file"}
      </Button>
    </fieldset>
  );
}

function size(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** The incident's files, and adding one while it is open. */
export function AttachmentsCard({ breach }: { breach: Breach }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [adding, setAdding] = React.useState(false);
  const [file, setFile] = React.useState<File | null>(null);
  const [kind, setKind] = React.useState<BreachAttachmentKind>("proof");
  const [note, setNote] = React.useState("");
  const open = breach.status === "open";
  const add = useMutation({
    mutationFn: () => addBreachAttachment(breach.breach_uuid, { file: file as File, kind, note }),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.detail(breach.breach_uuid), fresh);
      void qc.invalidateQueries({ queryKey: keys.breach.list() });
    },
  });

  async function save() {
    try {
      await add.mutateAsync();
      toast.success("File attached", "Kept with the incident as evidence.");
      setFile(null);
      setNote("");
      setAdding(false);
    } catch (err) {
      toast.error("Not attached", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card id="attachments" className="scroll-mt-20">
      <CardHeader className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle>
            <Paperclip className="mr-2 inline size-4" aria-hidden="true" />
            Attachments
          </CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            The email that reported it, proofs, chats, logs - kept as evidence. A file is never replaced or removed;
            every download is recorded on the audit trail.
          </p>
        </div>
        {open && !adding && (
          <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
            <Plus className="size-4" />
            Attach a file
          </Button>
        )}
      </CardHeader>
      <CardBody className="space-y-4">
        {adding && (
          <div className="space-y-3 rounded-lg border border-border p-3">
            <div className="grid gap-3 sm:grid-cols-[1fr_9rem]">
              <FileInput
                label="File"
                accept={ATTACHMENT_ACCEPT}
                maxBytes={ATTACHMENT_MAX_BYTES}
                file={file}
                onChange={setFile}
                required
              />
              <Field label="What it is">
                {(p) => (
                  <Select {...p} value={kind} onChange={(e) => setKind(e.target.value as BreachAttachmentKind)}>
                    {(Object.keys(ATTACHMENT_KIND) as BreachAttachmentKind[]).map((k) => (
                      <option key={k} value={k}>
                        {ATTACHMENT_KIND[k]}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            </div>
            <Field label="Note" hint="Optional: what it is, in a few words">
              {(p) => <Input {...p} value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />}
            </Field>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setAdding(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" disabled={!file} loading={add.isPending} onClick={save}>
                Attach
              </Button>
            </div>
          </div>
        )}
        {breach.attachments.length === 0 ? (
          <p className="text-sm text-text-muted">
            {open ? "No file yet." : "No file was kept with this incident."}
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {breach.attachments.map((a) => (
              <li key={a.attachment_uuid} className="flex flex-wrap items-start justify-between gap-2 py-2.5">
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge tone="neutral" dot={false}>
                      {ATTACHMENT_KIND[a.kind]}
                    </Badge>
                    <span className="break-all font-medium">{a.file_name}</span>
                  </p>
                  {a.note && <p className="mt-0.5 text-sm text-text-muted">{a.note}</p>}
                  <p className="mt-0.5 text-xs text-text-subtle">
                    {size(a.size_bytes)} · added {formatDateTime(a.added_at)} by {a.added_by_name ?? "unknown"} ·{" "}
                    <span className="font-mono" title={`SHA-256 ${a.sha256}`}>
                      {a.sha256.slice(0, 12)}
                    </span>
                  </p>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <a href={breachAttachmentUrl(breach.breach_uuid, a.attachment_uuid)} download>
                    <Download className="size-4" />
                    Download
                  </a>
                </Button>
              </li>
            ))}
          </ul>
        )}
        {!open && breach.attachments.length > 0 && (
          <Alert tone="info">The breach is closed: reopen it to attach more.</Alert>
        )}
      </CardBody>
    </Card>
  );
}
