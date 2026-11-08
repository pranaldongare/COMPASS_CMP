/**
 * Who a report to the organisation's board goes to (0064; the product owner's
 * decisions of 2026-11-07).
 *
 * The board's list, kept under Breach settings, is where a send starts, not
 * where it must end: whoever finalises may leave an address out of that one
 * report, or add one for it alone, and the list itself stays as it is. A
 * mandatory address goes with every report and cannot be left out.
 *
 * What the sender chose is kept as what they left out, not what they ticked,
 * so the list may move under an open window and the pick still means what was
 * meant: an address added meanwhile is ticked, one taken off simply goes, and
 * one marked mandatory meanwhile is in whatever was unticked. Who it goes to
 * is worked out at the press (`chosen`), and the server judges it again
 * against the list as it stands then.
 */
"use client";

import { Lock, UserPlus, X } from "lucide-react";
import * as React from "react";

import { Alert, Badge, Button, Field, Input } from "@/components/ui/primitives";
import type { BreachBoardEntry, BreachDocumentFinalise, Uuid } from "@/types";

export const addressCount = (n: number) => `${n} ${n === 1 ? "address" : "addresses"}`;

/** How many addresses one report may add for itself: the server's own limit
 *  (`BreachDocumentFinaliseIn.extra`), which it refuses in words no row of
 *  this picker could carry. */
export const MOST_EXTRA = 20;
const TOO_MANY_EXTRA = `At most ${MOST_EXTRA} addresses can be added for one report`;

/** Shaped like an email address: the server checks it properly. */
function looksLikeEmail(v: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
}

const same = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

export interface BoardAddress {
  full_name: string;
  email: string;
}

/**
 * A name, if there is one, and an address: what the list keeps, and what a
 * report may add for itself. A form of its own, so Enter adds the address, and
 * inside the finalise window it can never send the report.
 *
 * `refuse` is a refusal known here before asking anyone; `onAdd` answers
 * whether the fields go back to empty, which a refused add does not. `full`
 * says why nothing more may be added now: the form stands still and says so.
 */
export function BoardAddressForm({
  submitLabel,
  pending,
  refuse,
  full,
  onAdd,
}: {
  submitLabel: string;
  pending?: boolean;
  refuse?: (email: string) => string | null;
  full?: string | null;
  onAdd: (person: BoardAddress) => boolean | Promise<boolean>;
}) {
  const [person, setPerson] = React.useState<BoardAddress>({ full_name: "", email: "" });
  const [error, setError] = React.useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    // A form inside a dialog is still inside the page: its submit must not
    // reach anything around it.
    e.stopPropagation();
    if (!looksLikeEmail(person.email)) {
      setError("Enter an email address");
      return;
    }
    const refused = refuse?.(person.email) ?? null;
    if (refused) {
      setError(refused);
      return;
    }
    if (await onAdd({ full_name: person.full_name.trim(), email: person.email.trim() })) {
      setPerson({ full_name: "", email: "" });
    }
  }

  return (
    <form
      method="post"
      noValidate
      className="grid items-start gap-3 sm:grid-cols-[1fr_1fr_auto]"
      onSubmit={submit}
    >
      <Field label="Name" hint="Optional">
        {(p) => (
          <Input
            {...p}
            value={person.full_name}
            maxLength={200}
            disabled={Boolean(full)}
            onChange={(e) => setPerson({ ...person, full_name: e.target.value })}
          />
        )}
      </Field>
      <Field
        label="Mail ID"
        required
        hint={full ? `${full}.` : undefined}
        error={error ?? undefined}
      >
        {(p) => (
          <Input
            {...p}
            type="email"
            value={person.email}
            maxLength={255}
            disabled={Boolean(full)}
            onChange={(e) => {
              setPerson({ ...person, email: e.target.value });
              setError(null);
            }}
          />
        )}
      </Field>
      {/* Level with the boxes, below their labels, whatever is said under them. */}
      <Button
        type="submit"
        variant="secondary"
        className="sm:mt-7"
        disabled={!person.email.trim() || Boolean(full)}
        loading={pending}
      >
        <UserPlus className="size-4" />
        {submitLabel}
      </Button>
    </form>
  );
}

/** What the sender changed from "everyone on the list". */
export interface BoardPick {
  leftOut: ReadonlySet<Uuid>;
  extra: BoardAddress[];
}

export const NOTHING_CHANGED: BoardPick = { leftOut: new Set(), extra: [] };

/** Who a send goes to, from the list as it stands and what the sender
 *  changed: everyone on the list less those left out, every mandatory entry
 *  whatever was unticked, and the addresses added for this report. */
export function chosen(
  board: BreachBoardEntry[],
  pick: BoardPick,
): { body: BreachDocumentFinalise; count: number } {
  const recipients = board
    .filter((e) => e.mandatory || !pick.leftOut.has(e.recipient_uuid))
    .map((e) => e.recipient_uuid);
  const extra = pick.extra.map((x) => ({
    full_name: x.full_name.trim() || null,
    email: x.email.trim(),
  }));
  return { body: { recipients, extra }, count: recipients.length + extra.length };
}

const named = (p: { full_name: string | null; email: string }) =>
  p.full_name ? `${p.full_name}, ${p.email}` : p.email;

/**
 * "Who it goes to", at the foot of the finalise window: the board's list,
 * every entry ticked, and room for an address for this report alone.
 *
 * `holds` says the board's mail will wait for the first yes (a report to
 * CERT-In before the incident is recorded). `errors` are the server's refusals
 * of an added address, by its place in `pick.extra`.
 */
export function BoardPicker({
  board,
  pick,
  onChange,
  disabled,
  holds,
  errors = {},
}: {
  board: BreachBoardEntry[];
  pick: BoardPick;
  onChange: (pick: BoardPick) => void;
  disabled?: boolean;
  holds?: boolean;
  errors?: Record<number, string>;
}) {
  const { count } = chosen(board, pick);
  const anyMandatory = board.some((e) => e.mandatory);
  // A locked box says why to whoever cannot see the badge beside it.
  const ids = React.useId();

  function tick(uuid: Uuid, on: boolean) {
    const leftOut = new Set(pick.leftOut);
    if (on) leftOut.delete(uuid);
    else leftOut.add(uuid);
    onChange({ ...pick, leftOut });
  }

  return (
    <fieldset
      disabled={disabled}
      className="min-w-0 space-y-3 rounded-md border border-border p-3"
    >
      <legend className="px-1 text-sm font-medium">Who it goes to</legend>
      {holds && (
        <Alert tone="info" title="The board's mail waits for validation">
          The incident is not yet validated as a personal data breach. Finalising freezes
          the report now, and it goes to the addresses chosen here at the first Yes. If the
          incident is never validated as a personal data breach, the board is not sent it.
        </Alert>
      )}
      <p className="text-xs text-text-muted">
        Everyone on the organisation&apos;s board list is ticked. Untick anyone this report
        should not go to, or add an address for this report alone. The list itself stays as
        it is, under Breach settings.
      </p>
      {board.length > 0 && (
        <ul className="space-y-1.5">
          {board.map((e) => (
            <li
              key={e.recipient_uuid}
              className="flex min-w-0 flex-wrap items-center gap-2"
            >
              <label className="flex min-w-0 items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5 size-4 shrink-0 accent-[var(--accent)]"
                  checked={e.mandatory || !pick.leftOut.has(e.recipient_uuid)}
                  disabled={e.mandatory}
                  aria-describedby={e.mandatory ? `${ids}-${e.recipient_uuid}` : undefined}
                  onChange={(ev) => tick(e.recipient_uuid, ev.target.checked)}
                />
                <span className="min-w-0 break-words">{named(e)}</span>
              </label>
              {e.mandatory && (
                <Badge tone="neutral" id={`${ids}-${e.recipient_uuid}`}>
                  <Lock className="size-3" aria-hidden="true" />
                  Mandatory
                </Badge>
              )}
            </li>
          ))}
        </ul>
      )}
      {anyMandatory && (
        <p className="text-xs text-text-subtle">
          A mandatory address goes with every report and cannot be left out.
        </p>
      )}
      {pick.extra.length > 0 && (
        <ul className="space-y-1.5" aria-label="Added for this report">
          {pick.extra.map((x, i) => (
            <li key={`${x.email}-${i}`} className="space-y-0.5">
              <div className="flex min-w-0 flex-wrap items-center gap-2 text-sm">
                <span className="min-w-0 break-words">
                  {named({ full_name: x.full_name.trim() || null, email: x.email })}
                </span>
                <Badge tone="info">This report only</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Remove ${x.email} from this report`}
                  onClick={() =>
                    onChange({ ...pick, extra: pick.extra.filter((_, j) => j !== i) })
                  }
                >
                  <X className="size-4" />
                </Button>
              </div>
              {errors[i] && (
                <p role="alert" className="text-xs text-danger-text">
                  {errors[i]}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      <BoardAddressForm
        submitLabel="Add for this report"
        full={pick.extra.length >= MOST_EXTRA ? TOO_MANY_EXTRA : null}
        refuse={(email) =>
          pick.extra.length >= MOST_EXTRA
            ? TOO_MANY_EXTRA
            : board.some((e) => same(e.email, email))
              ? "Already on the board list: tick it above"
              : pick.extra.some((x) => same(x.email, email))
                ? "Already added to this report"
                : null
        }
        onAdd={(person) => {
          onChange({ ...pick, extra: [...pick.extra, person] });
          return true;
        }}
      />
      {count > 0 ? (
        <p className="text-xs text-text-muted">Goes to {addressCount(count)}.</p>
      ) : (
        <p className="text-xs font-medium text-warning-text">
          Choose at least one address.
        </p>
      )}
    </fieldset>
  );
}
