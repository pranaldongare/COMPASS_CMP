/**
 * Moving the date a ticket is due, from either side, with the reason.
 *
 * One control for a breach ticket's "Resolve by" and a rights ticket's
 * "Answer by" (2026-11-12): a breach ticket's date could be moved and a
 * rights ticket's could not, and the two windows are now the same shape. No
 * approval is asked: whoever moves it says why, the other side is told, and
 * the old date, the new date and the reason stay on the ticket and the trail.
 *
 * The date is a day in the reader's own calendar; what a day means to the
 * server - a date, or the end of that day - is the caller's to say.
 */
"use client";

import { CalendarClock } from "lucide-react";
import * as React from "react";

import { useDialogPart } from "@/components/ui/dialog";
import { Button, Field, Input, Textarea } from "@/components/ui/primitives";
import { todayLocal } from "@/lib/dates";
import { formatDate } from "@/lib/format";
import { useToast } from "@/providers";

function said(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

/** A date with no time (`YYYY-MM-DD`) as that day in the reader's own calendar.
 *  `new Date` reads it as midnight at Greenwich, the evening before for anyone
 *  west of it. */
function localDay(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function ChangeDate({
  label,
  current,
  latest,
  told,
  pending,
  onSave,
}: {
  /** What the date is called on this ticket: "Resolve by", "Answer by". */
  label: string;
  /** The date it has now, as `YYYY-MM-DD`, or none. */
  current: string | null;
  /** The last day it may be moved to, as `YYYY-MM-DD`, with why in `latestHint`. */
  latest?: { date: string; hint: string };
  /** Who hears of it, as a sentence. */
  told: string;
  pending: boolean;
  onSave: (body: { date: string; reason: string }) => Promise<unknown>;
}) {
  const toast = useToast();
  // Changed, or given up with its own Cancel: the window around it no longer
  // asks about the date and the reason - and still asks about a message.
  const { part, done } = useDialogPart();
  const earliest = todayLocal();
  const [changing, setChanging] = React.useState(false);
  const [date, setDate] = React.useState("");
  const [reason, setReason] = React.useState("");
  function start() {
    setDate(current && current >= earliest && (!latest || current <= latest.date) ? current : "");
    setReason("");
    setChanging(true);
  }
  async function save() {
    try {
      await onSave({ date, reason: reason.trim() });
      toast.success("Date changed", told);
      setChanging(false);
      done();
    } catch (err) {
      toast.error("Date not changed", said(err, "The server refused."));
    }
  }
  if (!changing) {
    return (
      <Button variant="secondary" size="sm" onClick={start}>
        <CalendarClock className="size-4" />
        Change the date
      </Button>
    );
  }
  const tooLate = Boolean(latest && date && date > latest.date);
  return (
    <div {...part} className="w-full space-y-3 rounded-md border border-border p-3">
      <p className="text-xs text-text-muted">
        {told} The old date, the new date and the reason are kept on the ticket, and the change is recorded in the audit trail.
      </p>
      <Field
        label={`New ${label.toLowerCase()} date`}
        required
        hint={latest ? `${latest.hint} (${formatDate(localDay(latest.date))}).` : undefined}
        error={tooLate ? `No later than ${formatDate(localDay(latest!.date))}.` : undefined}
      >
        {(p) => (
          <Input
            {...p}
            type="date"
            min={earliest}
            max={latest?.date}
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        )}
      </Field>
      <Field label="Reason" required hint="The other side reads this.">
        {(p) => (
          <Textarea {...p} rows={2} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} />
        )}
      </Field>
      <div className="flex justify-end gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            done();
            setChanging(false);
          }}
        >
          Cancel
        </Button>
        <Button
          variant="primary"
          size="sm"
          disabled={!date || date < earliest || date === current || tooLate || !reason.trim()}
          loading={pending}
          onClick={save}
        >
          Change the date
        </Button>
      </div>
    </div>
  );
}
