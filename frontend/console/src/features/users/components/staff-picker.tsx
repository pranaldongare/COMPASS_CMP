/**
 * Choosing a member of staff by typing (2026-11-12).
 *
 * One box. The people who match are listed under it as it is typed, and a
 * click - or the arrow keys and Enter - chooses one. It replaces a search box
 * ("Find them") above a drop-down ("Who") that had to be opened to see whether
 * the search had found anybody: two controls for one question, and the second
 * looked empty until the first was understood.
 *
 * A name is sealed, and is found through the hashed runs beside it: three
 * letters or more of a name, or the whole of an email address. So nothing is
 * listed before three characters, and the box says so.
 */
"use client";

import { Search, X } from "lucide-react";
import * as React from "react";

import { Button, Field, Input } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useUsers } from "@/features/users/queries";
import { cn } from "@/lib/format";
import type { User } from "@/types";

/** What the picker hands back: enough to show who was chosen. */
export type StaffChoice = Pick<User, "uuid" | "full_name" | "email" | "role">;

/** Roles that are not staff: nobody is assigned work through these accounts. */
const NOT_STAFF = new Set(["data_subject", "breach_holder"]);
const MIN_LETTERS = 3;
const SHOWN = 8;

function useDebounced<T>(value: T, ms: number): T {
  const [settled, setSettled] = React.useState(value);
  React.useEffect(() => {
    const timer = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return settled;
}

export function StaffPicker({
  label,
  value,
  onChange,
}: {
  label: string;
  value: StaffChoice | null;
  onChange: (next: StaffChoice | null) => void;
}) {
  const listId = React.useId();
  const [typed, setTyped] = React.useState("");
  const [active, setActive] = React.useState(0);
  const query = useDebounced(typed.trim(), 250);
  const searching = query.length >= MIN_LETTERS;
  const people = useUsers(searching ? { q: query, status: "active" } : {}, { enabled: searching });
  const matches = searching
    ? (people.data?.items ?? []).filter((u) => !NOT_STAFF.has(u.role)).slice(0, SHOWN)
    : [];
  const waiting = typed.trim() !== query || (searching && people.isLoading);

  function choose(person: StaffChoice) {
    onChange({ uuid: person.uuid, full_name: person.full_name, email: person.email, role: person.role });
    setTyped("");
    setActive(0);
  }

  if (value) {
    return (
      <div className="space-y-1.5">
        <p className="text-sm font-medium text-text">{label}</p>
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-accent-border bg-accent-subtle px-3 py-2">
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
              {value.full_name}
              <StatusBadge kind="role" value={value.role} dot={false} />
            </p>
            {value.email && <p className="truncate text-xs text-text-muted">{value.email}</p>}
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={() => onChange(null)}>
            <X className="size-4" />
            Change
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Field
        label={label}
        required
        hint="Enter three or more letters of a name, or a full email address."
      >
        {(p) => (
          <div className="relative">
            <Search
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-text-subtle"
              aria-hidden="true"
            />
            <Input
              {...p}
              role="combobox"
              aria-expanded={searching}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={matches.length ? `${listId}-${active}` : undefined}
              autoComplete="off"
              className="pl-9"
              placeholder="Search by name or email"
              value={typed}
              onChange={(e) => {
                setTyped(e.target.value);
                setActive(0);
              }}
              onKeyDown={(e) => {
                if (!matches.length) return;
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setActive((i) => (i + 1) % matches.length);
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setActive((i) => (i - 1 + matches.length) % matches.length);
                } else if (e.key === "Enter") {
                  e.preventDefault();
                  choose(matches[Math.min(active, matches.length - 1)]!);
                }
              }}
            />
          </div>
        )}
      </Field>

      {typed.trim().length >= MIN_LETTERS && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Matching staff"
          className="max-h-64 overflow-auto rounded-lg border border-border bg-surface p-1"
        >
          {waiting ? (
            <li className="px-3 py-2 text-sm text-text-subtle">Searching…</li>
          ) : people.error ? (
            <li className="px-3 py-2 text-sm text-danger-text">The search could not be completed.</li>
          ) : matches.length === 0 ? (
            <li className="px-3 py-2 text-sm text-text-subtle">
              No staff member matches “{query}”. Check the spelling, or enter the full email address.
            </li>
          ) : (
            matches.map((person, i) => (
              // The option itself is what is clicked: a button inside one is
              // not announced, and a click on the row's edge would miss it.
              // The keyboard is the box's: with aria-activedescendant, focus
              // never lands on an option, so it has no keys of its own.
              // eslint-disable-next-line jsx-a11y/click-events-have-key-events
              <li
                key={person.uuid}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                // Keeps the box focused, so the keyboard still works after a click.
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(person)}
                className={cn(
                  "flex cursor-pointer flex-wrap items-center justify-between gap-2 rounded-md px-3 py-2",
                  i === active ? "bg-accent-subtle" : "hover:bg-bg-inset",
                )}
              >
                <span className="min-w-0">
                  <span className="block text-sm font-medium">{person.full_name}</span>
                  {person.email && (
                    <span className="block truncate text-xs text-text-muted">{person.email}</span>
                  )}
                </span>
                <StatusBadge kind="role" value={person.role} dot={false} />
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
