/**
 * Release and close - or, for a grievance, decide.
 *
 * Nothing releases automatically. The DPO writes the response and signs off,
 * and the server refuses to call an answer with a hole in it "complete": a
 * holder that never returned its ticket is named in the response, and the
 * outcome has to say partial. On time with the gap named beats late.
 *
 * A grievance is decided here instead. Not upheld is a legitimate outcome, but
 * it has to be reasoned and in writing, and it carries the Board route.
 * Upheld names a remedy, and can re-run the request it was about.
 */
"use client";

import { Download, Send } from "lucide-react";
import * as React from "react";

import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Field, Select, Textarea } from "@/components/ui/primitives";
import { downloadResponse } from "@/features/rights/api";
import { OUTCOME_COPY } from "@/features/rights/components/copy";
import { useDecideGrievance, useRespond } from "@/features/rights/mutations";
import { formatDate, formatDateTime, saveBlob, shortHash } from "@/lib/format";
import { useToast } from "@/providers";
import type { RightsRequestDetail } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function RespondCard({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const respond = useRespond(r.request_uuid);
  const decide = useDecideGrievance(r.request_uuid);
  const closure = r.transitions.find((t) => t.via === "respond");
  const unreturned = r.holders.filter((h) => h.ticket_status === "issued" || h.ticket_status === "escalated");

  const [outcome, setOutcome] = React.useState(unreturned.length ? "partial" : "complete");
  const [text, setText] = React.useState("");
  const [upheld, setUpheld] = React.useState(true);
  const [remedy, setRemedy] = React.useState("");
  const [rerun, setRerun] = React.useState(Boolean(r.linked_reference));
  const [downloading, setDownloading] = React.useState(false);

  async function download() {
    setDownloading(true);
    try {
      const file = await downloadResponse(r.request_uuid);
      saveBlob(file.blob, file.filename);
    } catch (err) {
      toast.error("Could not download", messageOf(err, undefined as unknown as string));
    } finally {
      setDownloading(false);
    }
  }

  if (r.status === "closed") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Response</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            {r.outcome && OUTCOME_COPY[r.outcome].label}
            {r.responded_at && ` · ${formatDateTime(r.responded_at)}`}
            {r.download_expires_at && ` · downloadable by her until ${formatDate(r.download_expires_at)}`}
          </p>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="whitespace-pre-wrap text-sm">{r.response_text ?? r.refusal_reason}</p>
          {r.remedy_text && (
            <p className="text-sm">
              <span className="font-medium">Remedy: </span>
              {r.remedy_text}
            </p>
          )}
          {r.response_file_hash && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
              <span>File sha256 {shortHash(r.response_file_hash, 12)}</span>
              <Button variant="secondary" size="sm" loading={downloading} onClick={download}>
                <Download className="size-4" />
                Download the file
              </Button>
            </div>
          )}
        </CardBody>
      </Card>
    );
  }

  if (r.request_type === "grievance") {
    if (r.status === "received") return null;
    return (
      <Card>
        <CardHeader>
          <CardTitle>6 · Is it upheld?</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Was the original handling wrong, incomplete, or late? Either way: reasoned, in
            writing, with the Board route. Disagreement is not refusal.
          </p>
        </CardHeader>
        <CardBody className="space-y-3">
          <Field label="Decision">
            {(p) => (
              <Select {...p} value={upheld ? "upheld" : "not_upheld"} onChange={(e) => setUpheld(e.target.value === "upheld")}>
                <option value="upheld">Upheld</option>
                <option value="not_upheld">Not upheld</option>
              </Select>
            )}
          </Field>
          <Field label="What was found, and why" required>
            {(p) => <Textarea {...p} rows={4} value={text} onChange={(e) => setText(e.target.value)} />}
          </Field>
          {upheld && (
            <>
              <Field label="Remedy" hint="What is done about it, at no cost to her." required>
                {(p) => <Textarea {...p} rows={2} value={remedy} onChange={(e) => setRemedy(e.target.value)} />}
              </Field>
              {r.linked_reference && (
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" className="mt-0.5 size-4 rounded border-border-strong accent-[var(--accent)]" checked={rerun} onChange={(e) => setRerun(e.target.checked)} />
                  <span>
                    Re-run {r.linked_reference} as a new request linked to this decision.
                  </span>
                </label>
              )}
            </>
          )}
          <Button
            variant="primary"
            disabled={text.trim().length < 3 || (upheld && remedy.trim().length < 3)}
            loading={decide.isPending}
            onClick={async () => {
              try {
                const result = await decide.mutateAsync({ upheld, remedy_text: upheld ? remedy : null, response_text: text, rerun: upheld && rerun });
                toast.success(
                  upheld ? "Upheld" : "Not upheld",
                  result.rerun_reference ? `Re-run recorded as ${result.rerun_reference}.` : undefined,
                );
              } catch (err) {
                toast.error("Not decided", messageOf(err, "The server refused."));
              }
            }}
          >
            <Send className="size-4" />
            Decide and close
          </Button>
        </CardBody>
      </Card>
    );
  }

  if (!closure) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{r.request_type === "erasure" ? "10 · Respond and close" : "9–10 · Collate, review, release"}</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Third-party data removed. The DPO signs off - nothing releases automatically.
          {r.request_type === "access" && " An access response is a file she downloads from her own account."}
        </p>
      </CardHeader>
      <CardBody className="space-y-3">
        {!closure.allowed && (
          <Alert tone="warning">
            <p className="text-sm">{closure.blocked_by ?? "Not yet - finish the steps above."}</p>
          </Alert>
        )}
        {unreturned.length > 0 && (
          <Alert tone="warning">
            <p className="text-sm">
              {unreturned.map((h) => h.label).join(", ")} {unreturned.length === 1 ? "has" : "have"} not
              returned. The response can go out on time, but it is partial and the gap is named.
            </p>
          </Alert>
        )}
        <Field label="Outcome">
          {(p) => (
            <Select {...p} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
              <option value="complete" disabled={unreturned.length > 0}>Complete</option>
              <option value="partial">Partial - a gap is named</option>
              <option value="no_records">No records held anywhere</option>
            </Select>
          )}
        </Field>
        <Field
          label="The response"
          hint={
            r.request_type === "erasure"
              ? "What was erased, what was retained, and why each was decided."
              : "What she is being given, and what could not be provided."
          }
          required
        >
          {(p) => <Textarea {...p} rows={5} value={text} onChange={(e) => setText(e.target.value)} />}
        </Field>
        <Button
          variant="primary"
          disabled={!closure.allowed || text.trim().length < 3}
          loading={respond.isPending}
          onClick={async () => {
            try {
              await respond.mutateAsync({ outcome, response_text: text });
              toast.success("Released and closed", "She has been told the response is ready.");
            } catch (err) {
              toast.error("Not released", messageOf(err, "The server refused."));
            }
          }}
        >
          <Send className="size-4" />
          Release and close
        </Button>
      </CardBody>
    </Card>
  );
}
