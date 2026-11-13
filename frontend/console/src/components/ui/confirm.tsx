/**
 * Asking first, from inside a handler (2026-11-12).
 *
 * Whatever leaves the organisation - a response to a data principal, a ticket
 * to an outside processor, a report to the board - or ends something for good
 * is asked about in a pop-up that says who is told and what cannot be taken
 * back. `ConfirmDialog` is that pop-up; this is the way to raise it from an
 * existing click handler without giving every card another piece of state:
 *
 *     const confirm = useConfirm();
 *     async function release() {
 *       if (!(await confirm.ask({ title, consequence, confirmLabel }))) return;
 *       await respond.mutateAsync(...);
 *     }
 *     return <>{...}{confirm.dialog}</>;
 *
 * One question at a time: asking again answers the one before with "no", and
 * so does leaving the page. The pop-up closes on the answer, and the button
 * that was pressed shows the work in progress as it always did.
 */
"use client";

import * as React from "react";

import { ConfirmDialog } from "@/components/ui/dialog";

export interface Question {
  /** What is about to happen, as a question: "Release the response?" */
  title: string;
  /** Who is told, and what cannot be undone. */
  consequence: React.ReactNode;
  /** The verb, never "OK". */
  confirmLabel: string;
  /** `danger` for what destroys or ends; `primary` (the default) for what sends. */
  tone?: "danger" | "primary";
}

export function useConfirm(): {
  ask: (question: Question) => Promise<boolean>;
  dialog: React.ReactNode;
} {
  const [asked, setAsked] = React.useState<Question | null>(null);
  const answer = React.useRef<((yes: boolean) => void) | null>(null);

  const settle = React.useCallback((yes: boolean) => {
    const resolve = answer.current;
    answer.current = null;
    setAsked(null);
    resolve?.(yes);
  }, []);

  const ask = React.useCallback((question: Question) => {
    answer.current?.(false);
    return new Promise<boolean>((resolve) => {
      answer.current = resolve;
      setAsked(question);
    });
  }, []);

  // Gone before it was answered: that is a no.
  React.useEffect(
    () => () => {
      answer.current?.(false);
      answer.current = null;
    },
    [],
  );

  const dialog = asked ? (
    <ConfirmDialog
      open
      onOpenChange={(open) => !open && settle(false)}
      title={asked.title}
      consequence={asked.consequence}
      confirmLabel={asked.confirmLabel}
      tone={asked.tone ?? "primary"}
      onConfirm={() => settle(true)}
    />
  ) : null;

  return { ask, dialog };
}
