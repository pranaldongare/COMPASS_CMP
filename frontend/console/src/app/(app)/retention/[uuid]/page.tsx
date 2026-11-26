/**
 * One retention review (ADR 0047): who is in it, who was asked, what they
 * answered - and the officer's three moves on each answer: accept it, send it
 * back saying what is missing, or set an action aside as not needed. The
 * review closes once every action is accepted or set aside.
 *
 * People are shown by their numbers, never their names: what is decided here
 * is about the cohort, and the record of each consent is a click away.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { useConfirm } from "@/components/ui/confirm";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  EmptyState,
  Field,
  Skeleton,
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  ACTION_LABEL,
  KIND_LABEL,
  OUTCOME_LABEL,
  STATUS_LABEL,
  acceptAction,
  actionNotNeeded,
  actionTone,
  closeReview,
  downloadEvidence,
  downloadCertificate,
  getReview,
  retentionKeys,
  said,
  sendBackAction,
  type RetentionAction,
  type RetentionReviewDetail,
} from "@/features/retention/api";
import { formatDate, formatDateTime, saveBlob } from "@/lib/format";
import { useToast } from "@/providers";

const CHANNEL: Record<RetentionAction["channel"], string> = {
  console: "In the console",
  link: "By email link",
  automatic: "By the platform",
  none: "Nobody to ask",
};

function ActionCard({
  review,
  action,
}: {
  review: RetentionReviewDetail;
  action: RetentionAction;
}) {
  const toast = useToast();
  const client = useQueryClient();
  const confirm = useConfirm();
  const [back, setBack] = React.useState<string | null>(null);
  const [problem, setProblem] = React.useState<string | null>(null);
  const done = () => void client.invalidateQueries({ queryKey: retentionKeys.all });
  const fail = (err: unknown) => setProblem(said(err, "Not done. Try again in a moment."));

  const accept = useMutation({
    mutationFn: () => acceptAction(review.review_uuid, action.action_uuid),
    onSuccess: () => {
      done();
      toast.success("Answer accepted");
    },
    onError: fail,
  });
  const sendBack = useMutation({
    mutationFn: (reason: string) =>
      sendBackAction(review.review_uuid, action.action_uuid, reason),
    onSuccess: () => {
      setBack(null);
      done();
      toast.success("Sent back", `${action.label} is told what is missing.`);
    },
    onError: fail,
  });
  const aside = useMutation({
    mutationFn: () => actionNotNeeded(review.review_uuid, action.action_uuid),
    onSuccess: () => {
      done();
      toast.success("Set aside");
    },
    onError: fail,
  });

  async function onAccept() {
    const invites =
      review.kind === "validity" && action.kind === "owner" && action.reconsent;
    if (
      invites &&
      !(await confirm.ask({
        title: "Accept, and invite them again?",
        consequence: `Each of the ${review.people} people in this review is sent the project's consent link. This cannot be taken back.`,
        confirmLabel: "Accept and invite",
      }))
    )
      return;
    accept.mutate();
  }

  const open = action.status === "open" || action.status === "sent_back";
  return (
    <div className="space-y-3 rounded-lg border border-border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium">{action.label}</p>
          <p className="text-xs text-text-muted">
            {action.kind === "owner" ? "Answers for the project" : "Holds the data"} ·{" "}
            {CHANNEL[action.channel]}
            {action.assignee_name ? ` · ${action.assignee_name}` : ""}
          </p>
        </div>
        <Badge tone={actionTone(action.status, action.overdue)} dot>
          {action.overdue && open ? "Overdue" : ACTION_LABEL[action.status]}
        </Badge>
      </div>
      <DescriptionList>
        <DescriptionItem term="Answer by">{formatDate(action.due_at)}</DescriptionItem>
        {action.answered_at && (
          <DescriptionItem term="Answered">
            {formatDateTime(action.answered_at)}
            {action.answered_by_name ? ` by ${action.answered_by_name}` : " by link"}
          </DescriptionItem>
        )}
        {action.outcome && (
          <DescriptionItem term="Answer">
            {review.kind === "validity"
              ? action.reconsent
                ? "Invite them to consent again"
                : "Do not invite them again"
              : OUTCOME_LABEL[action.outcome]}
            {action.keep_until ? `, until ${formatDate(action.keep_until)}` : ""}
          </DescriptionItem>
        )}
        {action.reason && <DescriptionItem term="Reason">{action.reason}</DescriptionItem>}
        {action.evidence_hash && (
          <DescriptionItem term="Proof">
            <button
              type="button"
              className="text-accent-text underline underline-offset-2"
              onClick={async () => {
                try {
                  const got = await downloadEvidence(
                    review.review_uuid,
                    action.action_uuid,
                  );
                  saveBlob(got.blob, got.filename);
                } catch (err) {
                  setProblem(said(err, "The proof could not be downloaded."));
                }
              }}
            >
              {action.evidence_name ?? "Download"}
            </button>
            <span className="block font-mono text-xs text-text-muted">
              SHA-256 {action.evidence_hash.slice(0, 16)}…
            </span>
          </DescriptionItem>
        )}
        {action.sent_back_reason && (
          <DescriptionItem term="Sent back because">
            {action.sent_back_reason}
          </DescriptionItem>
        )}
        {action.accepted_at && (
          <DescriptionItem term="Accepted">
            {formatDateTime(action.accepted_at)}
            {action.accepted_by_name ? ` by ${action.accepted_by_name}` : ""}
          </DescriptionItem>
        )}
      </DescriptionList>
      {back !== null && (
        <form
          method="post"
          noValidate
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (back.trim()) sendBack.mutate(back.trim());
          }}
        >
          <Field label="What is missing" required>
            {(props) => (
              <Textarea
                {...props}
                rows={3}
                maxLength={2000}
                value={back}
                onChange={(e) => setBack(e.target.value)}
              />
            )}
          </Field>
          <div className="flex gap-2">
            <Button type="submit" disabled={!back.trim() || sendBack.isPending}>
              {sendBack.isPending ? "Sending…" : "Send it back"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setBack(null)}>
              Cancel
            </Button>
          </div>
        </form>
      )}
      {review.status !== "closed" && back === null && (
        <div className="flex flex-wrap gap-2">
          {action.status === "answered" && (
            <>
              <Button size="sm" onClick={onAccept} disabled={accept.isPending}>
                {accept.isPending ? "Accepting…" : "Accept"}
              </Button>
              <Button size="sm" variant="secondary" onClick={() => setBack("")}>
                Send back
              </Button>
            </>
          )}
          {open && (
            <Button
              size="sm"
              variant="ghost"
              disabled={aside.isPending}
              onClick={async () => {
                if (
                  await confirm.ask({
                    title: "Set this action aside?",
                    consequence: `${action.label} will not be asked again for this review.`,
                    confirmLabel: "Set aside",
                    tone: "danger",
                  })
                )
                  aside.mutate();
              }}
            >
              Not needed
            </Button>
          )}
        </div>
      )}
      {problem && <Alert tone="danger">{problem}</Alert>}
      {confirm.dialog}
    </div>
  );
}

function Close({ review }: { review: RetentionReviewDetail }) {
  const toast = useToast();
  const client = useQueryClient();
  const [note, setNote] = React.useState("");
  const [problem, setProblem] = React.useState<string | null>(null);
  const close = useMutation({
    mutationFn: () => closeReview(review.review_uuid, note.trim() || null),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: retentionKeys.all });
      toast.success("Review closed");
    },
    onError: (err) => setProblem(said(err, "Not closed. Try again in a moment.")),
  });
  const waiting = review.actions_list.filter(
    (a) => a.status !== "accepted" && a.status !== "not_needed",
  ).length;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Close the review</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        {waiting > 0 || review.actions_list.length === 0 ? (
          <p className="text-sm text-text-muted">
            {review.actions_list.length === 0
              ? "Nobody has been asked yet."
              : `${waiting} action${waiting === 1 ? " is" : "s are"} not settled yet.`}
          </p>
        ) : (
          <>
            <Field label="Note (optional)">
              {(props) => (
                <Textarea
                  {...props}
                  rows={2}
                  maxLength={2000}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              )}
            </Field>
            <Button onClick={() => close.mutate()} disabled={close.isPending}>
              {close.isPending ? "Closing…" : "Close the review"}
            </Button>
          </>
        )}
        {problem && <Alert tone="danger">{problem}</Alert>}
      </CardBody>
    </Card>
  );
}

function Certificate({ review }: { review: RetentionReviewDetail }) {
  const toast = useToast();
  const [busy, setBusy] = React.useState<"pdf" | "csv" | null>(null);
  async function get(format: "pdf" | "csv") {
    setBusy(format);
    try {
      const got = await downloadCertificate(review.review_uuid, format);
      saveBlob(got.blob, got.filename);
    } catch (err) {
      toast.error("Not downloaded", said(err, "Try again in a moment."));
    } finally {
      setBusy(null);
    }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Certificate</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        <p className="text-sm text-text-muted">
          Which consents, what each one asked answered, who accepted it and who closed the
          review. Consents by number; each download is on the audit trail.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => get("pdf")} disabled={busy !== null}>
            <Download className="size-4" aria-hidden="true" />
            {busy === "pdf" ? "Making…" : "PDF"}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => get("csv")}
            disabled={busy !== null}
          >
            <Download className="size-4" aria-hidden="true" />
            {busy === "csv" ? "Making…" : "CSV"}
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}

export default function RetentionReviewPage() {
  const { uuid } = useParams<{ uuid: string }>();
  const found = useQuery({
    queryKey: retentionKeys.review(uuid),
    queryFn: () => getReview(uuid),
  });
  const r = found.data;
  return (
    <>
      <PageHeader
        title={r ? r.reference : "Retention review"}
        description={r ? `${KIND_LABEL[r.kind]} · ${r.project_name}` : undefined}
        breadcrumb={
          <Link
            href="/retention"
            className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text"
          >
            <ArrowLeft className="size-4" aria-hidden="true" /> Retention
          </Link>
        }
      />
      {found.isLoading ? (
        <Skeleton className="h-96" />
      ) : found.error || !r ? (
        <Alert tone="danger">{said(found.error, "The review could not be loaded.")}</Alert>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Who is asked</CardTitle>
              </CardHeader>
              <CardBody className="space-y-3">
                {r.actions_list.length === 0 ? (
                  <EmptyState
                    title="Nobody asked yet"
                    description={
                      r.kind === "validity" && r.project_status !== "approved"
                        ? "The project is not active, so nobody is asked to invite these people again."
                        : "The people responsible are asked when the review falls due."
                    }
                  />
                ) : (
                  r.actions_list.map((a) => (
                    <ActionCard key={a.action_uuid} review={r} action={a} />
                  ))
                )}
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>People ({r.people_list.length})</CardTitle>
              </CardHeader>
              <div className="overflow-x-auto">
                <Table>
                  <thead>
                    <tr>
                      <Th>Person</Th>
                      <Th>Consent</Th>
                      <Th>Ended by</Th>
                      <Th>Due</Th>
                      <Th>State</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.people_list.map((p) => (
                      <Tr key={`${p.consent_uuid}`}>
                        <Td className="font-mono text-xs">P-{p.person_no}</Td>
                        <Td>
                          <Link
                            href={`/consents/${p.consent_uuid}`}
                            className="font-mono text-xs text-accent-text hover:underline"
                          >
                            C-{p.consent_no}
                          </Link>
                        </Td>
                        <Td>{p.ended_by === "withdrawal" ? "Withdrawal" : "Validity"}</Td>
                        <Td>{formatDate(p.due_at)}</Td>
                        <Td>
                          {p.state === "held" ? (
                            <Badge tone="warning">Legal hold</Badge>
                          ) : p.state === "renewed" ? (
                            <Badge tone="success">Consented again</Badge>
                          ) : (
                            <Badge>In the review</Badge>
                          )}
                          {p.notified_at && (
                            <span className="block text-xs text-text-muted">
                              Told {formatDate(p.notified_at)}
                            </span>
                          )}
                          {p.invited_at && (
                            <span className="block text-xs text-text-muted">
                              Invited {formatDate(p.invited_at)}
                            </span>
                          )}
                        </Td>
                      </Tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </Card>
          </div>
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>The review</CardTitle>
              </CardHeader>
              <CardBody>
                <DescriptionList>
                  <DescriptionItem term="Status">{STATUS_LABEL[r.status]}</DescriptionItem>
                  <DescriptionItem term="Purpose">
                    {r.purpose_code} · {r.purpose_name}
                  </DescriptionItem>
                  <DescriptionItem term={r.is_activity ? "HR activity" : "Project"}>
                    {r.project_name}
                  </DescriptionItem>
                  <DescriptionItem term="Falls due">
                    {formatDate(r.first_due_at)}
                    {r.last_due_at && r.last_due_at !== r.first_due_at
                      ? ` – ${formatDate(r.last_due_at)}`
                      : ""}
                  </DescriptionItem>
                  {r.validity_days != null && (
                    <DescriptionItem term="Consent lasts">
                      {r.validity_days} days
                    </DescriptionItem>
                  )}
                  {r.retention_days != null && (
                    <DescriptionItem term="Kept after it ends">
                      {r.retention_days} days
                    </DescriptionItem>
                  )}
                  <DescriptionItem term="People told before erasure">
                    {r.notify_before_erasure ? "Yes" : "No"}
                  </DescriptionItem>
                  {r.held > 0 && (
                    <DescriptionItem term="On legal hold">{r.held}</DescriptionItem>
                  )}
                  {r.renewed > 0 && (
                    <DescriptionItem term="Consented again">{r.renewed}</DescriptionItem>
                  )}
                  {r.closed_at && (
                    <DescriptionItem term="Closed">
                      {formatDateTime(r.closed_at)}
                      {r.closed_by_name ? ` by ${r.closed_by_name}` : ""}
                      {r.close_note ? `. ${r.close_note}` : ""}
                    </DescriptionItem>
                  )}
                </DescriptionList>
              </CardBody>
            </Card>
            {r.status !== "closed" ? <Close review={r} /> : <Certificate review={r} />}
          </div>
        </div>
      )}
    </>
  );
}
