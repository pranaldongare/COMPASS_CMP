/**
 * What I am asked to do about retention (ADR 0047): each review the Privacy
 * Office asked me to answer - as a project's DCO Admin, an HR activity's PoC,
 * or a processor's respondent - with the answer form beside the one opened.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Badge,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  EmptyState,
  Skeleton,
} from "@/components/ui/primitives";
import { AnswerForm } from "@/features/retention/answer-form";
import {
  ACTION_LABEL,
  KIND_LABEL,
  OUTCOME_LABEL,
  actionTone,
  answerAction,
  downloadMyEvidence,
  myAction,
  myActions,
  retentionKeys,
  said,
  type RetentionAnswer,
  uploadEvidence,
} from "@/features/retention/api";
import { cn, formatDate, saveBlob } from "@/lib/format";
import { useToast } from "@/providers";

function Opened({ uuid }: { uuid: string }) {
  const toast = useToast();
  const client = useQueryClient();
  const [problem, setProblem] = React.useState<string | null>(null);
  const found = useQuery({
    queryKey: retentionKeys.action(uuid),
    queryFn: () => myAction(uuid),
  });
  const answer = useMutation({
    mutationFn: async ({ body, proof }: { body: RetentionAnswer; proof: File | null }) => {
      if (proof) await uploadEvidence(uuid, proof);
      return answerAction(uuid, body);
    },
    onSuccess: () => {
      setProblem(null);
      void client.invalidateQueries({ queryKey: retentionKeys.mine });
      void client.invalidateQueries({ queryKey: retentionKeys.action(uuid) });
      toast.success("Answer sent", "The Privacy Office will accept it or send it back.");
    },
    onError: (err) => setProblem(said(err, "Not sent. Try again in a moment.")),
  });
  if (found.isLoading) return <Skeleton className="h-80" />;
  if (found.error || !found.data)
    return <Alert tone="danger">{said(found.error, "This could not be loaded.")}</Alert>;
  const { action, review } = found.data;
  const open = action.status === "open" || action.status === "sent_back";
  return (
    <Card>
      <CardHeader>
        <CardTitle>{review.reference}</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          {KIND_LABEL[review.kind]} · {review.project_name}
        </p>
      </CardHeader>
      <CardBody className="space-y-5">
        <DescriptionList>
          <DescriptionItem term="Purpose">
            {review.purpose_code} · {review.purpose_name}
          </DescriptionItem>
          <DescriptionItem term="People">{review.people}</DescriptionItem>
          <DescriptionItem
            term={review.kind === "validity" ? "Consent runs out" : "Data due to go"}
          >
            {formatDate(review.first_due_at)}
            {review.last_due_at && review.last_due_at !== review.first_due_at
              ? ` – ${formatDate(review.last_due_at)}`
              : ""}
          </DescriptionItem>
          <DescriptionItem term="Asked of">{action.label}</DescriptionItem>
          <DescriptionItem term="Answer by">{formatDate(action.due_at)}</DescriptionItem>
        </DescriptionList>
        {action.sent_back_reason && action.status === "sent_back" && (
          <Alert tone="warning" title="Sent back">
            {action.sent_back_reason}
          </Alert>
        )}
        {open ? (
          <AnswerForm
            kind={review.kind}
            pending={answer.isPending}
            problem={problem}
            onAnswer={(body, proof) => answer.mutate({ body, proof })}
          />
        ) : (
          <>
            {action.evidence_hash && (
              <p className="text-sm">
                Proof attached:{" "}
                <button
                  type="button"
                  className="text-accent-text underline underline-offset-2"
                  onClick={async () => {
                    const got = await downloadMyEvidence(uuid);
                    saveBlob(got.blob, got.filename);
                  }}
                >
                  {action.evidence_name ?? "download"}
                </button>
              </p>
            )}
            <Alert tone={action.status === "accepted" ? "success" : "info"}>
              {ACTION_LABEL[action.status]}
              {action.outcome && review.kind === "retention"
                ? `: ${OUTCOME_LABEL[action.outcome]}`
                : ""}
              {review.kind === "validity" && action.reconsent != null
                ? action.reconsent
                  ? ": invite them again"
                  : ": do not invite them"
                : ""}
              .
            </Alert>
          </>
        )}
      </CardBody>
    </Card>
  );
}

export default function RetentionActionsPage() {
  const mine = useQuery({ queryKey: retentionKeys.mine, queryFn: myActions });
  const [picked, setPicked] = React.useState<string | null>(null);
  const first = mine.data?.find((a) => a.status === "open" || a.status === "sent_back");
  const current = picked ?? first?.action_uuid ?? mine.data?.[0]?.action_uuid ?? null;
  return (
    <>
      <PageHeader title="Retention actions" />
      {mine.isLoading ? (
        <Skeleton className="h-64" />
      ) : mine.error ? (
        <Alert tone="danger">{said(mine.error, "Your actions could not be loaded.")}</Alert>
      ) : !mine.data?.length ? (
        <EmptyState
          title="Nothing to answer"
          description="When consents for a project you answer for run out, or their data must go, the Privacy Office asks you here."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <ul className="space-y-2" aria-label="Your retention actions">
            {mine.data.map((a) => (
              <li key={a.action_uuid}>
                <button
                  type="button"
                  aria-current={current === a.action_uuid}
                  onClick={() => setPicked(a.action_uuid)}
                  className={cn(
                    "bg-bg-raised w-full rounded-lg border p-3 text-left text-sm",
                    current === a.action_uuid ? "border-accent-border" : "border-border",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs">{a.reference}</span>
                    <Badge tone={actionTone(a.status, a.overdue)} dot>
                      {a.overdue && (a.status === "open" || a.status === "sent_back")
                        ? "Overdue"
                        : ACTION_LABEL[a.status]}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-text-muted">
                    {KIND_LABEL[a.review_kind]} · answer by {formatDate(a.due_at)}
                  </p>
                </button>
              </li>
            ))}
          </ul>
          {current && <Opened key={current} uuid={current} />}
        </div>
      )}
    </>
  );
}
