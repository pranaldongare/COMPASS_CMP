/**
 * The answer to a retention action (ADR 0047), as the one asked gives it.
 *
 * A validity review asks one thing of its owner: should these people be
 * invited to consent again? (Only while the project is active; the invitation
 * goes once the officer accepts the answer.) A retention review asks what was
 * done with the data: erased, anonymised (with the reason it could not be
 * erased), kept (with the reason and the date it will be looked at again),
 * or not held at all.
 *
 * A file may go with it - a deletion log, a screenshot, a letter - as proof;
 * the page sends the file first, then the answer.
 */
"use client";

import * as React from "react";

import { Alert, Button, Field, Input, Textarea } from "@/components/ui/primitives";
import type { Outcome, RetentionAnswer, ReviewKind } from "@/features/retention/types";
import { cn } from "@/lib/format";

const CHOICES: { value: Outcome; label: string; hint: string }[] = [
  {
    value: "erased",
    label: "Erased",
    hint: "Deleted everywhere we hold it, backups included.",
  },
  {
    value: "anonymised",
    label: "Anonymised",
    hint: "Nobody can be identified from what is left. Say why it was not erased.",
  },
  {
    value: "kept",
    label: "Kept",
    hint: "A law or a claim needs it kept. Say which, and when it will be looked at again.",
  },
  { value: "not_held", label: "Not held", hint: "We hold none of these people's data." },
];

export function AnswerForm({
  kind,
  pending,
  problem,
  onAnswer,
}: {
  kind: ReviewKind;
  pending: boolean;
  problem: string | null;
  onAnswer: (body: RetentionAnswer, proof: File | null) => void;
}) {
  const [outcome, setOutcome] = React.useState<Outcome | null>(null);
  const [reconsent, setReconsent] = React.useState<boolean | null>(null);
  const [reason, setReason] = React.useState("");
  const [until, setUntil] = React.useState("");
  const [proof, setProof] = React.useState<File | null>(null);
  const [local, setLocal] = React.useState<string | null>(null);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setLocal(null);
    if (kind === "validity") {
      if (reconsent === null) {
        setLocal("Choose whether to invite these people to consent again.");
        return;
      }
      onAnswer({ reconsent, reason: reason.trim() || null }, proof);
      return;
    }
    if (!outcome) {
      setLocal("Choose what was done.");
      return;
    }
    if ((outcome === "anonymised" || outcome === "kept") && !reason.trim()) {
      setLocal("Say why. Anonymising instead of erasing, and keeping, each need a reason.");
      return;
    }
    if (outcome === "kept" && !until) {
      setLocal("Give the date it will be looked at again.");
      return;
    }
    onAnswer(
      {
        outcome,
        reason: reason.trim() || null,
        keep_until: outcome === "kept" ? until : null,
      },
      proof,
    );
  }

  const needsReason = outcome === "anonymised" || outcome === "kept";
  return (
    <form method="post" noValidate onSubmit={submit} className="space-y-4">
      {kind === "validity" ? (
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">
            Should these people be asked to consent again?
          </legend>
          {[
            {
              v: true,
              label: "Yes, invite them",
              hint: "The project still needs this data. Each person gets the project's consent link once the Privacy Office accepts this answer.",
            },
            {
              v: false,
              label: "No",
              hint: "Let the consents run out. What happens to the data then follows the purpose's retention.",
            },
          ].map((c) => (
            <label
              key={String(c.v)}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm",
                reconsent === c.v
                  ? "border-accent-border bg-accent-subtle"
                  : "border-border",
              )}
            >
              <input
                type="radio"
                name="reconsent"
                className="mt-1"
                checked={reconsent === c.v}
                onChange={() => setReconsent(c.v)}
              />
              <span className="font-medium">
                {c.label}
                <span className="block text-xs font-normal text-text-muted">{c.hint}</span>
              </span>
            </label>
          ))}
        </fieldset>
      ) : (
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">What was done with the data?</legend>
          {CHOICES.map((c) => (
            <label
              key={c.value}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm",
                outcome === c.value
                  ? "border-accent-border bg-accent-subtle"
                  : "border-border",
              )}
            >
              <input
                type="radio"
                name="outcome"
                className="mt-1"
                checked={outcome === c.value}
                onChange={() => setOutcome(c.value)}
              />
              <span className="font-medium">
                {c.label}
                <span className="block text-xs font-normal text-text-muted">{c.hint}</span>
              </span>
            </label>
          ))}
        </fieldset>
      )}
      <Field
        label={needsReason ? "Reason" : "Note (optional)"}
        required={needsReason}
        hint={
          needsReason
            ? "Kept on the record and shown to the Privacy Office."
            : "Anything the Privacy Office should know."
        }
      >
        {(props) => (
          <Textarea
            {...props}
            rows={3}
            maxLength={2000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        )}
      </Field>
      {outcome === "kept" && kind === "retention" && (
        <Field label="Look at it again on" required>
          {(props) => (
            <Input
              {...props}
              type="date"
              value={until}
              onChange={(e) => setUntil(e.target.value)}
            />
          )}
        </Field>
      )}
      {kind === "retention" && (
        <Field
          label="Proof (optional)"
          hint="A deletion log, a screenshot or a letter: PDF, PNG, JPG, CSV or text, up to 25 MB."
        >
          {(props) => (
            <Input
              {...props}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.csv,.txt"
              onChange={(e) => setProof(e.target.files?.[0] ?? null)}
            />
          )}
        </Field>
      )}
      {(local || problem) && <Alert tone="danger">{local ?? problem}</Alert>}
      <Button type="submit" disabled={pending}>
        {pending ? "Sending…" : "Send the answer"}
      </Button>
    </form>
  );
}
