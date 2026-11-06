/**
 * The reports a breach calls for (0059, ADR 0037).
 *
 * One path for each: a draft that starts from the register and is the
 * office's to rewrite; finalising, which freezes it and mails the
 * organisation's board; then, for a regulator's report, filing: the proof of
 * internal approval, the mail a person sent, when, and the reference that came
 * back. The proof may come first and the rest later, and any finalised version
 * may be filed, because what was sent is not always the newest. The platform
 * never sends to the DPDP Board or to CERT-In. The board's own report is done
 * when its mail lands, not when it is finalised. What each report may do now is
 * the server's answer; a refusal shows its sentence.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Download,
  FilePlus2,
  FileText,
  Mail,
  Paperclip,
  RotateCcw,
  Save,
  Send,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { FileInput } from "@/components/forms";
import { ConfirmDialog, Dialog, DialogContent, DialogSaved } from "@/components/ui/dialog";
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
  Textarea,
} from "@/components/ui/primitives";
import {
  addBreachDocumentProof,
  breachAttachmentUrl,
  breachDocumentPdf,
  draftBreachDocument,
  editBreachDocument,
  fileBreachDocument,
  finaliseBreachDocument,
  getBreachDocuments,
  resendBreachDocument,
} from "@/features/breach/api";
import {
  ATTACHMENT_ACCEPT,
  ATTACHMENT_KIND,
  ATTACHMENT_MAX_BYTES,
} from "@/features/breach/components/attachments";
import { instant, messageOf } from "@/features/breach/components/record-breach";
import { formatDateTime, saveBlob } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import { useOptionalAuth } from "@/providers/auth-provider";
import type {
  Breach,
  BreachDocument,
  BreachDocumentKind,
  BreachDocumentKindView,
  BreachDocumentMail,
  BreachDocumentMailRecipient,
  BreachDocumentProof,
  BreachDocumentState,
  BreachDocuments,
} from "@/types";

const STATE: Record<BreachDocumentState, { label: string; tone: "info" | "warning" | "success" }> = {
  draft: { label: "Draft", tone: "info" },
  finalised: { label: "Finalised", tone: "warning" },
  filed: { label: "Sent", tone: "success" },
};

/** Mail the worker may yet reach. What has sat queued too long was lost, and
 *  only Try again moves it; one to an address taken off the list is not waited
 *  for at all. */
const onItsWay = (mail: BreachDocumentMail) =>
  mail.recipients.filter((r) => r.status === "queued" && !r.removed).length - mail.stale;

/** The version sending again is about: a later one has replaced the words. */
const newestSent = (view: BreachDocumentKindView) => view.versions.find((v) => v.state !== "draft");

/** Whether Try again would do anything for this version. `retryable` is what it
 *  would queue. A board report that reached somebody and left its duty waiting
 *  queues nothing, but the press re-reads the duty, and nothing else will. */
function mayTryAgain(view: BreachDocumentKindView, doc: BreachDocument) {
  if (doc.mail.retryable > 0) return true;
  return (
    view.kind === "org_board" &&
    view.duty_state === "outstanding" &&
    doc.mail.delivered > 0 &&
    doc.mail.queued === 0 &&
    newestSent(view)?.report_uuid === doc.report_uuid
  );
}

/** The draft a write has just left for this kind of report. */
const draftIn = (fresh: BreachDocuments, kind: BreachDocumentKind) =>
  fresh.kinds.find((k) => k.kind === kind)?.versions.find((v) => v.state === "draft")?.report_uuid ?? null;

const addressCount = (n: number) => `${n} ${n === 1 ? "address" : "addresses"}`;

/** Where a version stands. A report to the organisation's board has gone when
 *  its mail has landed, not when it was finalised. */
function standing(view: BreachDocumentKindView, doc: BreachDocument) {
  if (view.goes_to_regulator || doc.state !== "finalised") return STATE[doc.state];
  if (doc.mail.delivered > 0) return STATE.filed;
  return onItsWay(doc.mail) > 0
    ? ({ label: "Sending", tone: "info" } as const)
    : ({ label: "Not reached", tone: "warning" } as const);
}

/** While a mail is on its way, look again soon: whoever just finalised should
 *  not wait a quarter of a minute to see that it went. Read afresh on arrival
 *  too: who is on the board's list comes from here, and may just have changed.
 *  `watchUntil` keeps it looking closely for a moment after a press. */
export function useBreachDocuments(uuid: string, watchUntil = 0) {
  return useQuery<BreachDocuments>({
    queryKey: keys.breach.reports(uuid),
    queryFn: () => getBreachDocuments(uuid),
    refetchOnMount: "always",
    refetchInterval: (q) =>
      Date.now() < watchUntil || q.state.data?.kinds.some((k) => k.versions.some((v) => onItsWay(v.mail) > 0))
        ? 2_000
        : 30_000,
  });
}

function useAfter(breach: Breach) {
  const qc = useQueryClient();
  return (fresh: BreachDocuments) => {
    qc.setQueryData(keys.breach.reports(breach.breach_uuid), fresh);
    void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
    void qc.invalidateQueries({ queryKey: ["breaches"] });
  };
}

/** The API's limit on one section. */
const SECTION_MAX = 20_000;

/** The drafting window: every section, saved, then finalised. It stays while
 *  the row or the duty around it changes, and goes only when told to, or when
 *  somebody else has finalised the draft. */
function ReportEditor({
  breach,
  doc,
  recipients,
  blocked,
  onClose,
}: {
  breach: Breach;
  doc: BreachDocument;
  recipients: number;
  /** Why this may not be finalised now, in the server's words. A draft can
   *  still be read and saved: it is the words going anywhere that waits. */
  blocked?: string | null;
  onClose: () => void;
}) {
  const toast = useToast();
  const after = useAfter(breach);
  const toBoard = doc.kind === "org_board";
  const [bodies, setBodies] = React.useState<Record<string, string>>(() =>
    Object.fromEntries(doc.sections.map((s) => [s.key, s.body ?? ""])),
  );
  const [dirty, setDirty] = React.useState(false);
  // Each save: closing the window need not ask about what is saved.
  const [saves, setSaves] = React.useState(0);
  const save = useMutation({
    mutationFn: () => editBreachDocument(breach.breach_uuid, doc.report_uuid, bodies),
    onSuccess: (fresh) => {
      after(fresh);
      setDirty(false);
      setSaves((n) => n + 1);
    },
  });
  const finalise = useMutation({
    // Always the words on the screen: what is frozen is what was read.
    mutationFn: async () => {
      await save.mutateAsync();
      return finaliseBreachDocument(breach.breach_uuid, doc.report_uuid);
    },
    onSuccess: after,
  });
  // The words stand still while they go: what is typed now would not be sent.
  const busy = save.isPending || finalise.isPending;
  const missing = doc.sections.filter((s) => s.required && !bodies[s.key]?.trim());
  // Nothing here can be saved now, so it goes, and says so. Not when the
  // finalising was this window's own, however the answer and a poll fall.
  const overtaken = doc.state !== "draft" && !finalise.isPending && !finalise.isSuccess;
  React.useEffect(() => {
    if (!overtaken) return;
    toast.warning(
      "That draft has been finalised",
      "Somebody else finalised it while it was open here. Anything not saved is not in it.",
    );
    onClose();
  }, [overtaken, toast, onClose]);

  async function keep() {
    try {
      await save.mutateAsync();
      toast.success("Draft saved");
    } catch (err) {
      toast.error("Not saved", messageOf(err, "The server refused."));
    }
  }

  async function go() {
    try {
      await finalise.mutateAsync();
      toast.success(
        toBoard ? "Sent to the organisation's board" : "Finalised",
        toBoard
          ? `Mailing ${addressCount(recipients)}. The duty completes when the mail lands.`
          : "The organisation's board has been mailed. Nothing has gone to the regulator.",
      );
      onClose();
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        size="lg"
        title={`${doc.title} · version ${doc.version}`}
        description={
          toBoard
            ? "Started from what the incident holds. Change anything you need to, then send it to the addresses on the organisation's board list."
            : "Started from what the incident holds. Change anything you need to. Finalising freezes it and mails the organisation's board, for its information: it does not go to the regulator."
        }
      >
        <DialogSaved count={saves} />
        <div className="space-y-3">
          {blocked && (
            <Alert tone="warning" title="This can't be finalised for now">
              {blocked}.
            </Alert>
          )}
          {recipients === 0 && (
            <Alert tone="warning" title="Nobody is on the organisation's board list">
              Add their addresses under{" "}
              <Link
                href="/breach-settings"
                target="_blank"
                rel="noreferrer"
                className="font-medium text-accent-text hover:underline"
              >
                Breach settings
              </Link>{" "}
              before this can go.
            </Alert>
          )}
          {doc.sections.map((s) => (
            <Field
              key={s.key}
              label={s.label}
              required={s.required}
              // A paste past the limit is cut short with no word from the browser.
              hint={
                (bodies[s.key]?.length ?? 0) >= SECTION_MAX
                  ? `At the limit of ${SECTION_MAX.toLocaleString("en-IN")} characters`
                  : undefined
              }
            >
              {(p) => (
                <Textarea
                  {...p}
                  rows={4}
                  disabled={busy}
                  maxLength={SECTION_MAX}
                  value={bodies[s.key] ?? ""}
                  onChange={(e) => {
                    setBodies({ ...bodies, [s.key]: e.target.value });
                    setDirty(true);
                  }}
                />
              )}
            </Field>
          ))}
          {missing.length > 0 && (
            <p className="text-xs text-text-muted">
              Still to write: {missing.map((s) => s.label).join("; ")}.
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="secondary"
              disabled={!dirty || finalise.isPending}
              loading={save.isPending}
              onClick={keep}
            >
              <Save className="size-4" />
              Save draft
            </Button>
            <Button
              variant="primary"
              disabled={missing.length > 0 || recipients === 0 || Boolean(blocked) || save.isPending}
              loading={finalise.isPending}
              onClick={go}
            >
              <Send className="size-4" />
              {toBoard ? "Send to the board" : "Finalise and tell the board"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** Each proof kept with a version, to open. Every download is on the trail. */
function ProofLinks({ breach, proofs }: { breach: Breach; proofs: BreachDocumentProof[] }) {
  if (proofs.length === 0) return null;
  return (
    <ul className="space-y-0.5 text-xs text-text-muted">
      {proofs.map((p) => (
        <li key={p.attachment_uuid} className="flex min-w-0 items-start gap-1.5">
          <Paperclip className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span className="min-w-0 break-words">
            {ATTACHMENT_KIND[p.kind]}:{" "}
            <a
              href={breachAttachmentUrl(breach.breach_uuid, p.attachment_uuid)}
              download
              className="font-medium text-accent-text hover:underline"
            >
              {p.file_name}
            </a>
          </span>
        </li>
      ))}
    </ul>
  );
}

const PROOF_FIELDS: Record<
  BreachDocumentProof["kind"],
  { label: string; another: string; hint?: string }
> = {
  approval: {
    label: "Proof of internal approval",
    another: "Add another proof of internal approval",
  },
  sent_mail: {
    label: "The mail sent to the regulator",
    another: "Add another mail sent to the regulator",
    hint: "Saved from your mailbox, or as a PDF",
  },
};

/** What is kept of one kind of proof, and room for another: a file is never
 *  replaced, so a wrong one is put right by adding the right one beside it. */
function ProofField({
  breach,
  doc,
  kind,
  file,
  onChange,
}: {
  breach: Breach;
  doc: BreachDocument;
  kind: BreachDocumentProof["kind"];
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  const kept = doc.evidence.filter((e) => e.kind === kind);
  const field = PROOF_FIELDS[kind];
  return (
    <div className="space-y-1.5">
      <ProofLinks breach={breach} proofs={kept} />
      {/* Afresh after each upload: a file input goes on showing what it held. */}
      <FileInput
        key={kept.length}
        label={kept.length > 0 ? field.another : field.label}
        hint={kept.length > 0 ? "Optional" : field.hint}
        accept={ATTACHMENT_ACCEPT}
        maxBytes={ATTACHMENT_MAX_BYTES}
        file={file}
        onChange={onChange}
        required={kept.length === 0}
      />
    </div>
  );
}

/** A person sent it: keep the proof, and record when and what came back. The
 *  proof may come before the rest is known; recording it still needs it all. */
function FilingDialog({
  breach,
  doc,
  needsReference,
  blocked,
  onClose,
}: {
  breach: Breach;
  doc: BreachDocument;
  needsReference: boolean;
  /** Why this may not be recorded now, in the server's words. The window stays,
   *  with what has been typed, and picks up again when the block clears. */
  blocked: string | null;
  onClose: () => void;
}) {
  const toast = useToast();
  const after = useAfter(breach);
  const has = (kind: "approval" | "sent_mail") => doc.evidence.some((e) => e.kind === kind);
  const [approval, setApproval] = React.useState<File | null>(null);
  const [sent, setSent] = React.useState<File | null>(null);
  const [when, setWhen] = React.useState("");
  const [reference, setReference] = React.useState("");
  const at = instant(when);
  const ready =
    (has("approval") || approval !== null) &&
    (has("sent_mail") || sent !== null) &&
    at !== null &&
    (!needsReference || reference.trim() !== "");

  // Each proof is kept as it arrives: a file is never replaced, so a second
  // try after a refusal must not send one the first try already kept.
  async function keepProofs() {
    if (approval) {
      after(
        await addBreachDocumentProof(breach.breach_uuid, doc.report_uuid, {
          file: approval,
          kind: "approval",
        }),
      );
      setApproval(null);
    }
    if (sent) {
      after(
        await addBreachDocumentProof(breach.breach_uuid, doc.report_uuid, {
          file: sent,
          kind: "sent_mail",
        }),
      );
      setSent(null);
    }
  }
  const attach = useMutation({ mutationFn: keepProofs });
  const file = useMutation({
    mutationFn: async () => {
      await keepProofs();
      return fileBreachDocument(breach.breach_uuid, doc.report_uuid, {
        filed_at: at as string,
        reference: reference.trim() || null,
      });
    },
    onSuccess: after,
  });

  async function later() {
    try {
      await attach.mutateAsync();
      toast.success("Proof attached", "It stays with this version. Record it as sent when the rest is known.");
      onClose();
    } catch (err) {
      toast.error("Not attached", messageOf(err, "The server refused."));
    }
  }

  async function save() {
    try {
      await file.mutateAsync();
      toast.success("Recorded as sent", "The report, its proof and the reference are on the record.");
      onClose();
    } catch (err) {
      toast.error("Not recorded", messageOf(err, "The server refused."));
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title={`Record as sent · ${doc.title} · version ${doc.version}`}
        description="The platform does not send this. Send it to the regulator through its own channel, then keep the proof here."
      >
        <div className="space-y-3">
          {blocked && (
            <Alert tone="warning" title="This can't be recorded for now">
              {blocked}.
            </Alert>
          )}
          <ProofField breach={breach} doc={doc} kind="approval" file={approval} onChange={setApproval} />
          <ProofField breach={breach} doc={doc} kind="sent_mail" file={sent} onChange={setSent} />
          <Field label="Sent at" hint="When it was sent, not when you are recording it" required>
            {(p) => (
              <Input {...p} type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
            )}
          </Field>
          <Field
            label="Reference returned"
            hint={needsReference ? "Acknowledgement or filing number" : "Optional"}
            required={needsReference}
          >
            {(p) => (
              <Input
                {...p}
                value={reference}
                maxLength={200}
                onChange={(e) => setReference(e.target.value)}
              />
            )}
          </Field>
          <p className="text-xs text-text-muted">
            Not everything known yet? Attach and finish later keeps the files; the time and the reference are entered
            when you come back to record it.
          </p>
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="secondary"
              disabled={(!approval && !sent) || Boolean(blocked) || file.isPending}
              loading={attach.isPending}
              onClick={later}
            >
              <Paperclip className="size-4" />
              Attach and finish later
            </Button>
            <Button
              variant="primary"
              disabled={!ready || Boolean(blocked) || attach.isPending}
              loading={file.isPending}
              onClick={save}
            >
              <CheckCircle2 className="size-4" />
              Record as sent
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** One address and what became of it. Taken off the list, it is mailed no more,
 *  so that is what it says rather than a state Try again would not change. */
function addressState(r: BreachDocumentMailRecipient): string {
  const at = formatDateTime(r.recorded_at);
  if (r.removed) {
    return r.status === "delivered" ? `delivered ${at}, since removed from the list` : "removed from the list";
  }
  return `${r.status} ${at}${r.error ? ` (${r.error})` : ""}`;
}

/** Why nothing can go, and where to put that right for those who can. */
function NobodyOnTheList() {
  const canReach = useOptionalAuth()?.me?.nav.includes("breach-settings");
  return (
    <>
      Nobody is on the organisation&apos;s board list, so there is nowhere to send this.
      {canReach && (
        <>
          {" "}
          Add an address under{" "}
          <Link href="/breach-settings" className="font-medium text-accent-text hover:underline">
            Breach settings
          </Link>
          .
        </>
      )}
    </>
  );
}

function MailLine({
  breach,
  view,
  doc,
  listed,
  onPressed,
}: {
  breach: Breach;
  view: BreachDocumentKindView;
  doc: BreachDocument;
  /** How many addresses are on the board's list now. */
  listed: number;
  onPressed: () => void;
}) {
  const toast = useToast();
  const after = useAfter(breach);
  const again = useMutation({
    mutationFn: () => resendBreachDocument(breach.breach_uuid, doc.report_uuid),
    onSuccess: after,
  });
  const { delivered, queued, failed, stale, retryable, recipients } = doc.mail;
  // An address taken off the list is in no count, and its line still says so.
  if (delivered + queued + failed === 0 && recipients.length === 0) return null;
  const moving = onItsWay(doc.mail);
  const open = breach.status === "open";
  const unreached = failed > 0 || stale > 0;
  // Not in the mail's account yet: on the list since this version went.
  const added = Math.max(retryable - failed - stale, 0);
  const nowhere =
    open &&
    listed === 0 &&
    delivered === 0 &&
    view.blocked_by === null &&
    newestSent(view)?.report_uuid === doc.report_uuid;

  // A press says what it did: a re-queued mail, or none at all, can look the
  // same on the screen as a press that went nowhere.
  async function press() {
    try {
      const fresh = await again.mutateAsync();
      const done = fresh.kinds.find((k) => k.kind === view.kind)?.duty_state === "done";
      if (fresh.queued > 0) {
        toast.success("Sending again", `Mailing ${addressCount(fresh.queued)}.`);
      } else if (done && view.duty_state === "outstanding") {
        toast.success("Duty completed", "The mail had already reached the board, so nothing went again.");
      } else {
        toast.info("Nothing to send", "Every address on the list has this report, or it is still on its way.");
      }
    } catch (err) {
      toast.error("Not sent", messageOf(err, "The server refused."));
    } finally {
      onPressed();
    }
  }

  return (
    <div className="space-y-1">
      <p className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
        <Mail className="size-3.5" aria-hidden="true" />
        <span>
          Organisation&apos;s board: {delivered} delivered
          {moving > 0 && `, ${moving} on the way`}
          {stale > 0 && <span className="font-medium text-danger-text">, {stale} held up</span>}
          {failed > 0 && <span className="font-medium text-danger-text">, {failed} failed</span>}
          {added > 0 && `, ${added} added to the list since`}
        </span>
        {open && mayTryAgain(view, doc) && (
          <Button variant="ghost" size="sm" loading={again.isPending} onClick={press}>
            <RotateCcw className="size-3.5" />
            Try again
          </Button>
        )}
      </p>
      {nowhere && (
        <p className="text-xs font-medium text-warning-text">
          <NobodyOnTheList />
        </p>
      )}
      {recipients.length > 0 && (
        <details open={unreached || nowhere} className="text-xs text-text-muted">
          <summary className="cursor-pointer">Address by address ({recipients.length})</summary>
          <ul className="mt-1 space-y-0.5">
            {recipients.map((r) => (
              <li key={r.recipient_uuid} className="break-words">
                {r.full_name ? `${r.full_name}, ${r.email}` : r.email}: {addressState(r)}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function PdfButton({ breach, doc }: { breach: Breach; doc: BreachDocument }) {
  const toast = useToast();
  const [busy, setBusy] = React.useState(false);
  async function get() {
    setBusy(true);
    try {
      const got = await breachDocumentPdf(breach.breach_uuid, doc.report_uuid);
      saveBlob(got.blob, got.filename);
    } catch (err) {
      toast.error("Could not download", messageOf(err, "The server refused."));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Button variant="ghost" size="sm" loading={busy} onClick={get}>
      <Download className="size-4" />
      PDF
    </Button>
  );
}

/** What became of one finalised version: when, its mail, its proof, its PDF. */
function VersionRecord({
  breach,
  view,
  doc,
  listed,
  onPressed,
  onFile,
}: {
  breach: Breach;
  view: BreachDocumentKindView;
  doc: BreachDocument;
  listed: number;
  onPressed: () => void;
  onFile?: () => void;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs text-text-muted">
        Finalised {formatDateTime(doc.finalised_at)} by {doc.finalised_by_name ?? "unknown"}
        {doc.state === "filed" && (
          <>
            {" · sent to the regulator "}
            {formatDateTime(doc.filed_at)}
            {doc.filed_reference && `, reference ${doc.filed_reference}`}
          </>
        )}
      </p>
      <MailLine breach={breach} view={view} doc={doc} listed={listed} onPressed={onPressed} />
      <ProofLinks breach={breach} proofs={doc.evidence} />
      <div className="flex flex-wrap items-center gap-2">
        <PdfButton breach={breach} doc={doc} />
        {onFile && (
          <Button variant="secondary" size="sm" onClick={onFile}>
            <CheckCircle2 className="size-4" />
            Record as sent
          </Button>
        )}
      </div>
    </div>
  );
}

function ReportRow({
  breach,
  view,
  recipients,
  onPressed,
}: {
  breach: Breach;
  view: BreachDocumentKindView;
  recipients: number;
  onPressed: () => void;
}) {
  const toast = useToast();
  const after = useAfter(breach);
  // By its uuid: this draft, not whichever draft comes next.
  const [editing, setEditing] = React.useState<string | null>(null);
  // By its uuid: any finalised version can be the one that was sent, and the
  // dialog reads each new proof from the list as it stands.
  const [filing, setFiling] = React.useState<string | null>(null);
  const [confirming, setConfirming] = React.useState(false);
  const start = useMutation({
    mutationFn: () => draftBreachDocument(breach.breach_uuid, view.kind),
    onSuccess: after,
  });
  const open = breach.status === "open";
  const [latest, ...earlier] = view.versions;
  const badge = latest && standing(view, latest);
  const mayFile = (v: BreachDocument) =>
    view.goes_to_regulator && v.state === "finalised" && view.blocked_by === null;
  // Not `mayFile`: what may be offered changes under an open window, which stays.
  const filingDoc = view.versions.find((v) => v.report_uuid === filing && v.state === "finalised");
  const editingDoc = view.versions.find((v) => v.report_uuid === editing);
  // Nothing that still needs doing stays folded away, and nothing else opens.
  const earlierOpen = open && earlier.some((v) => mayFile(v) || mayTryAgain(view, v));

  async function begin() {
    try {
      setEditing(draftIn(await start.mutateAsync(), view.kind));
    } catch (err) {
      toast.error("Not started", messageOf(err, "The server refused."));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <li className="space-y-2 px-5 py-4" data-testid={`report-${view.kind}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
            {view.title}
            {latest && badge && (
              <Badge tone={badge.tone} dot={false}>
                {badge.label}
                {latest.version > 1 ? ` · version ${latest.version}` : ""}
              </Badge>
            )}
          </p>
          <p className="text-xs text-text-subtle">
            {view.basis}
            {view.kind === "closure" && " · optional"}
          </p>
        </div>
        {open && (
          <div className="flex flex-wrap gap-2">
            {latest?.state === "draft" ? (
              <Button variant="primary" size="sm" onClick={() => setEditing(latest.report_uuid)}>
                <FileText className="size-4" />
                Continue the draft
              </Button>
            ) : (
              <>
                {latest && mayFile(latest) && (
                  <Button variant="primary" size="sm" onClick={() => setFiling(latest.report_uuid)}>
                    <CheckCircle2 className="size-4" />
                    Record as sent
                  </Button>
                )}
                <Button
                  variant={latest ? "ghost" : "secondary"}
                  size="sm"
                  disabled={view.blocked_by !== null}
                  title={view.blocked_by ?? undefined}
                  loading={start.isPending}
                  onClick={() => (latest && mayFile(latest) ? setConfirming(true) : begin())}
                >
                  <FilePlus2 className="size-4" />
                  {latest ? "New version" : "Draft it"}
                </Button>
              </>
            )}
          </div>
        )}
      </div>
      {open && view.blocked_by && <p className="text-xs text-text-muted">{view.blocked_by}.</p>}
      {latest && latest.state !== "draft" && (
        <VersionRecord breach={breach} view={view} doc={latest} listed={recipients} onPressed={onPressed} />
      )}
      {earlier.length > 0 && (
        <details open={earlierOpen} className="text-xs text-text-muted">
          <summary className="cursor-pointer">Earlier versions ({earlier.length})</summary>
          <ul className="mt-2 space-y-3">
            {earlier.map((v) => (
              <li key={v.report_uuid} className="space-y-1">
                <p className="font-medium text-text">
                  Version {v.version}, {standing(view, v).label.toLowerCase()}
                </p>
                <VersionRecord
                  breach={breach}
                  view={view}
                  doc={v}
                  listed={recipients}
                  onPressed={onPressed}
                  onFile={open && mayFile(v) ? () => setFiling(v.report_uuid) : undefined}
                />
              </li>
            ))}
          </ul>
        </details>
      )}
      {editingDoc && (
        <ReportEditor
          breach={breach}
          doc={editingDoc}
          recipients={recipients}
          blocked={view.blocked_by}
          onClose={() => setEditing(null)}
        />
      )}
      {filingDoc && (
        <FilingDialog
          breach={breach}
          doc={filingDoc}
          needsReference={view.duty !== null}
          blocked={view.blocked_by}
          onClose={() => setFiling(null)}
        />
      )}
      {confirming && latest && (
        <ConfirmDialog
          open
          onOpenChange={setConfirming}
          title={`Start version ${latest.version + 1}?`}
          consequence={`Version ${latest.version} is finalised and not yet recorded as sent. If it is the one that went to the regulator, it can still be recorded as sent, under Earlier versions.`}
          confirmLabel="Start a new version"
          tone="primary"
          loading={start.isPending}
          onConfirm={begin}
        />
      )}
    </li>
  );
}

/** How long a press of Try again keeps the page looking closely, whatever the
 *  answer said: what it queued may be moving before the next slow read. */
const PRESS_WATCH_MS = 20_000;

export function ReportsCard({ breach }: { breach: Breach }) {
  const [watchUntil, setWatchUntil] = React.useState(0);
  const query = useBreachDocuments(breach.breach_uuid, watchUntil);
  // The board's report first: it is what is due soonest.
  return (
    <Card id="reports" className="scroll-mt-20">
      <CardHeader>
        <CardTitle>Reports</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Draft each report here. Finalising it mails the organisation&apos;s board, and the board&apos;s own report
          completes its duty when that mail lands: if every address fails the duty stays outstanding, and Try again
          sends it again. The platform does not send anything to the DPDP Board or CERT-In: send it yourself, then record
          it with the proof of internal approval and the mail you sent. That is what completes those duties.
        </p>
      </CardHeader>
      {breach.status !== "open" && (
        <CardBody>
          <Alert tone="info">The breach is closed. A report can only be written, sent or recorded after reopening it.</Alert>
        </CardBody>
      )}
      {query.isLoading ? (
        <CardBody>
          <Skeleton className="h-40" />
        </CardBody>
      ) : query.error && !query.data ? (
        <CardBody>
          <Alert tone="danger">{query.error.message}</Alert>
        </CardBody>
      ) : (
        <ul className="divide-y divide-border">
          {query.data?.kinds.map((view) => (
            <ReportRow
              key={view.kind}
              breach={breach}
              view={view}
              recipients={query.data?.board_recipients ?? 0}
              onPressed={() => setWatchUntil(Date.now() + PRESS_WATCH_MS)}
            />
          ))}
        </ul>
      )}
    </Card>
  );
}

/** "Notify Organization Board": the report's pop-up, wherever the button is.
 *  Offered while the board's duty stands on a recorded breach, which is from a
 *  validation of yes; an incident logged before that rule may hold the duty
 *  early, and has no report to write yet. That duty completes when the mail
 *  lands, so while it is going there is no new version to offer, and where
 *  sending again would do something the way on is Try again, not a second
 *  mailing. An editor already open stays, whatever happens to the duty. */
export function NotifyBoardButton({ breach }: { breach: Breach }) {
  const toast = useToast();
  const qc = useQueryClient();
  const after = useAfter(breach);
  const query = useBreachDocuments(breach.breach_uuid);
  // By its uuid, as on the Reports tab.
  const [editing, setEditing] = React.useState<string | null>(null);
  const kind: BreachDocumentKind = "org_board";
  const view = query.data?.kinds.find((k) => k.kind === kind);
  const start = useMutation({
    mutationFn: () => draftBreachDocument(breach.breach_uuid, kind),
    onSuccess: after,
  });
  const due =
    breach.breach_reference !== null &&
    breach.obligations.some((d) => d.duty === kind && d.state === "outstanding");
  const latest = view?.versions[0];
  const sent = latest?.state === "finalised" ? latest : null;
  const sending = sent !== null && onItsWay(sent.mail) > 0;
  // The worker completes the duty, so nothing here says so: read the breach
  // again the moment the mail has run its course.
  const landed = due && sent !== null && !sending;
  React.useEffect(() => {
    if (landed) void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid), exact: true });
    // The account is committed before the duty, so the first read can come too
    // soon: go again when the reports say the duty has moved.
  }, [landed, view?.duty_state, qc, breach.breach_uuid]);
  const draft = latest?.state === "draft" ? latest : null;
  const editingDoc = view?.versions.find((v) => v.report_uuid === editing);

  async function open() {
    try {
      setEditing(draft ? draft.report_uuid : draftIn(await start.mutateAsync(), kind));
    } catch (err) {
      toast.error("Not started", messageOf(err, "The server refused."));
    }
  }

  function control() {
    // The reports are the fresher word on the duty: the breach may not have caught up.
    if (breach.status !== "open" || !due || view?.duty_state !== "outstanding") return null;
    if (sending) {
      return (
        <span role="status" className="inline-flex items-center gap-1.5 text-xs text-text-muted">
          <Mail className="size-3.5" aria-hidden="true" />
          Sending to the board
        </span>
      );
    }
    if (sent && mayTryAgain(view, sent)) {
      return (
        <Button variant="secondary" size="sm" asChild>
          <a href="#reports">
            <RotateCcw className="size-4" />
            {sent.mail.delivered > 0 ? "Delivered: finish on the Reports tab" : "Not reached: Try again on the Reports tab"}
          </a>
        </Button>
      );
    }
    if (sent && sent.mail.delivered === 0 && query.data?.board_recipients === 0) {
      return (
        <span role="status" className="text-xs font-medium text-warning-text">
          <NobodyOnTheList />
        </span>
      );
    }
    return (
      <Button variant="primary" size="sm" loading={start.isPending} onClick={open}>
        <Send className="size-4" />
        Notify Organization Board
      </Button>
    );
  }

  return (
    <>
      {control()}
      {editingDoc && (
        <ReportEditor
          breach={breach}
          doc={editingDoc}
          recipients={query.data?.board_recipients ?? 0}
          blocked={view?.blocked_by}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}
