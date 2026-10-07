/**
 * Telling the people a breach touched (S3-03).
 *
 * The five things Rule 7(1) requires, drafted, approved, then sent. Nothing
 * sends on its own: the server refuses to send before approval and refuses to
 * approve with any of the five empty, and says which. A send writes the notice
 * to every listed person's account at once and queues her email and SMS; a
 * second send adds only what is missing. An update is a new version.
 *
 * The account underneath - per version and channel, how many people are
 * delivered, queued or failed - is what the Board's report quotes
 * (Rule 7(2)(b)(vi)).
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FilePlus2, Megaphone, Save, Send } from "lucide-react";
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
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { approveNotice, draftNotice, editNotice, getNotices, sendNotice } from "@/features/breach/api";
import { messageOf } from "@/features/breach/components/record-breach";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { Breach, BreachNotice, BreachNotices, BreachNoticeWords } from "@/types";

const CHANNEL: Record<string, string> = { portal: "Their account", email: "Email", sms: "SMS" };

/** A first draft from the assessment, which says most of it already. */
function fromAssessment(breach: Breach): BreachNoticeWords {
  const a = breach.assessment;
  return {
    what_happened: a?.nature_extent ?? "",
    consequences: a?.consequences ?? "",
    measures: a?.mitigation ?? "",
    protective_steps: a?.protective_steps ?? "",
    contact: a?.contact_point ?? "",
  };
}

function wordsOf(n: BreachNotice): BreachNoticeWords {
  const { what_happened, consequences, measures, protective_steps, contact } = n;
  return { what_happened, consequences, measures, protective_steps, contact };
}

function Account({ data }: { data: BreachNotices }) {
  if (data.account.length === 0) return <p className="text-sm text-text-muted">Nothing sent yet.</p>;
  return (
    <>
      <Table>
        <caption className="sr-only">Who received which version, by channel</caption>
        <thead>
          <tr>
            <Th>Version</Th>
            <Th>Channel</Th>
            <Th>Delivered</Th>
            <Th>Queued</Th>
            <Th>Failed</Th>
          </tr>
        </thead>
        <tbody>
          {[...new Set(data.account.map((r) => `${r.version}:${r.channel}`))].map((key) => {
            const [version, channel] = key.split(":");
            const of = (status: string) =>
              data.account.find((r) => `${r.version}` === version && r.channel === channel && r.status === status)
                ?.people ?? 0;
            return (
              <Tr key={key}>
                <Td>{version}</Td>
                <Td>{CHANNEL[channel]}</Td>
                <Td>{of("delivered")}</Td>
                <Td>{of("queued")}</Td>
                <Td className={of("failed") ? "text-danger-text" : undefined}>{of("failed")}</Td>
              </Tr>
            );
          })}
        </tbody>
      </Table>
      {data.failures.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer">Failed deliveries ({data.failures.length})</summary>
          <ul className="mt-2 space-y-1">
            {data.failures.map((f) => (
              <li key={`${f.person_uuid ?? f.contact_uuid}:${f.version}:${f.channel}`}>
                {f.full_name ?? "No name"} - {CHANNEL[f.channel]}, version {f.version}, attempt {f.attempt}:{" "}
                {String(f.detail.error ?? "failed")} ({formatDateTime(f.recorded_at)})
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-text-muted">Send again to make a new attempt at each failed delivery.</p>
        </details>
      )}
    </>
  );
}

export function NoticesCard({ breach }: { breach: Breach }) {
  const toast = useToast();
  const qc = useQueryClient();
  const query = useQuery<BreachNotices>({
    queryKey: keys.breach.notices(breach.breach_uuid),
    queryFn: () => getNotices(breach.breach_uuid),
    // While deliveries are on their way, look again soon: the worker sends in
    // well under a second, and somebody who has just pressed Send should not
    // wait a quarter of a minute to see that it went. Otherwise every 15 s.
    refetchInterval: (q) =>
      q.state.data?.account.some((a) => a.status === "queued" && a.people > 0) ? 2_000 : 15_000,
  });
  const data = query.data;
  const draft = data?.versions.find((v) => v.state === "draft") ?? null;
  const approved = [...(data?.versions ?? [])].reverse().find((v) => v.state === "approved") ?? null;
  const [words, setWords] = React.useState<BreachNoticeWords | null>(null);
  const shown = words ?? (draft ? wordsOf(draft) : null);

  const after = (fresh: BreachNotices) => {
    qc.setQueryData(keys.breach.notices(breach.breach_uuid), fresh);
    void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
  };
  const start = useMutation({ mutationFn: (w: BreachNoticeWords) => draftNotice(breach.breach_uuid, w), onSuccess: after });
  const save = useMutation({
    mutationFn: (w: BreachNoticeWords) => editNotice(breach.breach_uuid, draft!.notice_uuid, w),
    onSuccess: after,
  });
  const approve = useMutation({ mutationFn: () => approveNotice(breach.breach_uuid, draft!.notice_uuid), onSuccess: after });
  const send = useMutation({ mutationFn: () => sendNotice(breach.breach_uuid), onSuccess: after });

  async function act(what: () => Promise<unknown>, ok: string, detail?: string) {
    try {
      await what();
      setWords(null);
      toast.success(ok, detail);
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
    }
  }

  const open = breach.status === "open";
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Megaphone className="mr-2 inline size-4" aria-hidden="true" />
          Telling the people it touched
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Rule 7(1): concise, clear and plain, without delay, to each person&apos;s account and their registered email or mobile;
          to someone with no account, by email and SMS. Nothing is sent until you approve and send it. The words go to
          everyone listed: name nobody.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {data && (
          <p className="text-sm">
            {data.listed === 0
              ? "Nobody is listed as touched yet."
              : `${data.listed - data.unnotified} of ${data.listed} listed ${data.listed === 1 ? "person has" : "people have"} been notified on every channel.` +
                (data.contacts ? ` ${data.contacts} of them ${data.contacts === 1 ? "has" : "have"} no account and ${data.contacts === 1 ? "is" : "are"} told by email and SMS.` : "")}
          </p>
        )}

        {approved && !draft && (
          <div className="rounded-md border border-border p-3 text-sm">
            <p className="font-medium">
              Version {approved.version} <Badge tone="success">Approved</Badge>
            </p>
            <p className="text-xs text-text-subtle">
              {formatDateTime(approved.approved_at)} by {approved.approved_by_name ?? "unknown"}
            </p>
            <dl className="mt-2 space-y-2">
              {data?.contents.map((c) => (
                <div key={c.key}>
                  <dt className="text-xs text-text-muted">{c.label}</dt>
                  <dd className="whitespace-pre-wrap">{approved[c.key]}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {draft && shown && data && (
          <div className="space-y-3 rounded-md border border-border p-3">
            <p className="text-sm font-medium">
              Version {draft.version} <Badge tone="info">Draft</Badge>
            </p>
            {data.contents.map((c) => (
              <Field key={c.key} label={c.label} required>
                {(p) => (
                  <Textarea
                    {...p}
                    value={shown[c.key]}
                    disabled={!open}
                    onChange={(e) => setWords({ ...shown, [c.key]: e.target.value })}
                  />
                )}
              </Field>
            ))}
            {open && (
              <div className="flex flex-wrap justify-end gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={words === null}
                  loading={save.isPending}
                  onClick={() => act(() => save.mutateAsync(shown), "Draft saved")}
                >
                  <Save className="size-4" />
                  Save draft
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={words !== null}
                  loading={approve.isPending}
                  onClick={() => act(() => approve.mutateAsync(), "Notice approved", "Send it when you are ready.")}
                >
                  <CheckCircle2 className="size-4" />
                  Approve
                </Button>
              </div>
            )}
            {words !== null && <p className="text-xs text-text-muted">Save the draft before approving it.</p>}
          </div>
        )}

        {open && data && !draft && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={start.isPending}
              onClick={() =>
                act(
                  () => start.mutateAsync(approved ? wordsOf(approved) : fromAssessment(breach)),
                  approved ? "Update started" : "Draft started",
                  "Complete all five, save, then approve.",
                )
              }
            >
              <FilePlus2 className="size-4" />
              {approved ? "Start an updated notice" : "Draft the notice"}
            </Button>
            {approved && (
              <Button
                variant="primary"
                size="sm"
                disabled={data.listed === 0 || data.send_blocked_by !== null}
                title={data.send_blocked_by ?? undefined}
                loading={send.isPending}
                onClick={() =>
                  act(() => send.mutateAsync(), `Version ${approved.version} sent`, "Each email and SMS is sent by the worker.")
                }
              >
                <Send className="size-4" />
                Send version {approved.version}
              </Button>
            )}
          </div>
        )}
        {/* The server's reason, in its words: an incident still being
            validated may have its notice drafted and approved, not sent. */}
        {data?.send_blocked_by && open && (
          <Alert tone="info" title="Not sent before the breach is recorded">
            {data.send_blocked_by}
          </Alert>
        )}
        {data && data.listed === 0 && open && (
          <Alert tone="info" title="Confirm who it touched first">
            A notice goes to the people listed under Who it touched.
          </Alert>
        )}

        {data && <Account data={data} />}
      </CardBody>
    </Card>
  );
}
