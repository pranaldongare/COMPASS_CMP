/**
 * The questions the audit trail can be asked, as controls.
 *
 * Every filter here maps to one query parameter on `GET /audit`, and the same
 * parameters drive the summary and the CSV export, so what the panel says is
 * exactly what the table, the numbers and the file contain.
 *
 * "About" is the one that matters most and used to be missing: a data
 * principal, a member of staff, a consent record, a processor, a data source,
 * a project, a notice, a site or a rights request, found by typing a few
 * letters of its name. The server's lookup says which filter each answer
 * feeds (subject, actor or entity), so the panel never guesses.
 *
 * The vocabulary - which tables, which events, which pickers - comes from the
 * server, not a list typed here. The last such list was eight tables behind.
 */
"use client";

import { Search, X } from "lucide-react";
import * as React from "react";

import { Button, Field, Input, Select } from "@/components/ui/primitives";
import { useAuditLookup } from "@/features/audit/queries";
import { humanise } from "@/lib/format";
import type { AuditLookupHit, AuditVocabulary } from "@/types";

/** Everything the page carries in its URL. Strings, because that is what a
 *  query string is; empty means "not set". */
export interface AuditFilterState {
  q: string;
  event_group: string;
  event_type: string;
  entity_type: string;
  actor_role: string;
  from: string;
  to: string;
  subject: string;
  actor: string;
  entity: string;
  /** The name of the picked person or record, for the chip. Display only. */
  label: string;
}

export const EMPTY_FILTERS: AuditFilterState = {
  q: "",
  event_group: "",
  event_type: "",
  entity_type: "",
  actor_role: "",
  from: "",
  to: "",
  subject: "",
  actor: "",
  entity: "",
  label: "",
};

export const FILTER_KEYS = Object.keys(EMPTY_FILTERS) as (keyof AuditFilterState)[];

const ROLES = ["dpo", "admin", "dco", "dco_admin", "rco", "rnd_user", "data_subject"];

/** The API parameters for a state: dates widened to whole days, display-only
 *  keys dropped, empties dropped. */
export function toApiParams(f: AuditFilterState): Record<string, string> {
  const out: Record<string, string> = {};
  if (f.q) out.q = f.q;
  if (f.event_type) out.event_type = f.event_type;
  else if (f.event_group) out.event_group = f.event_group;
  if (f.actor_role) out.actor_role = f.actor_role;
  if (f.subject) out.subject = f.subject;
  if (f.actor) out.actor = f.actor;
  if (f.entity_type) out.entity_type = f.entity_type;
  if (f.entity && f.entity_type) out.entity = f.entity;
  if (f.from) out.from = `${f.from}T00:00:00Z`;
  if (f.to) out.to = `${f.to}T23:59:59Z`;
  return out;
}

export function AuditFilters({
  value,
  vocabulary,
  onChange,
}: {
  value: AuditFilterState;
  vocabulary: AuditVocabulary | undefined;
  onChange: (next: Partial<AuditFilterState>) => void;
}) {
  const eventTypes = (vocabulary?.event_types ?? []).filter(
    (e) => !value.event_group || e.group === value.event_group,
  );

  return (
    <div className="mb-4 space-y-3 rounded-xl border border-border bg-surface/60 p-3 shadow-[var(--shadow-sm)]">
      <div className="flex flex-wrap items-end gap-3">
        {/* Keyed on the value in force, so a chip that clears the search also
            clears the box, without an effect writing state. */}
        <SearchForm key={value.q} initial={value.q} onSubmit={(q) => onChange({ q })} />

        <AboutPicker vocabulary={vocabulary} onPick={onChange} />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <Field label="Area">
          {(p) => (
            <Select
              {...p}
              className="w-48"
              value={value.event_group}
              onChange={(e) => onChange({ event_group: e.target.value, event_type: "" })}
            >
              <option value="">Every area</option>
              {(vocabulary?.event_groups ?? []).map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label="Event">
          {(p) => (
            <Select
              {...p}
              className="w-60"
              value={value.event_type}
              onChange={(e) => {
                const chosen = e.target.value;
                const group = eventTypes.find((t) => t.value === chosen)?.group;
                onChange({ event_type: chosen, event_group: group ?? value.event_group });
              }}
            >
              <option value="">
                Every event{value.event_group ? " in this area" : ""}
              </option>
              {eventTypes.map((t) => (
                <option key={t.value} value={t.value}>
                  {value.event_group ? t.label : `${t.group_label}: ${t.label}`}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label="Record type">
          {(p) => (
            <Select
              {...p}
              className="w-48"
              value={value.entity_type}
              onChange={(e) =>
                onChange({ entity_type: e.target.value, entity: "", label: "" })
              }
            >
              <option value="">Every table</option>
              {(vocabulary?.entity_types ?? []).map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label="Actor role">
          {(p) => (
            <Select
              {...p}
              className="w-40"
              value={value.actor_role}
              onChange={(e) => onChange({ actor_role: e.target.value })}
            >
              <option value="">Any role</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {humanise(r)}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label="From">
          {(p) => (
            <Input
              {...p}
              type="date"
              value={value.from}
              max={value.to || undefined}
              onChange={(e) => onChange({ from: e.target.value })}
            />
          )}
        </Field>
        <Field label="To">
          {(p) => (
            <Input
              {...p}
              type="date"
              value={value.to}
              min={value.from || undefined}
              onChange={(e) => onChange({ to: e.target.value })}
            />
          )}
        </Field>
      </div>
    </div>
  );
}

function SearchForm({
  initial,
  onSubmit,
}: {
  initial: string;
  onSubmit: (q: string) => void;
}) {
  const [term, setTerm] = React.useState(initial);
  return (
    <form
      method="post"
      className="flex items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(term.trim());
      }}
    >
      <Field
        label="Search"
        hint="A reference, a purpose, a reason, a name: anything the trail recorded."
      >
        {(p) => (
          <div className="relative w-72">
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-text-subtle"
              aria-hidden="true"
            />
            <Input
              {...p}
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="RR-2026-000042, Pune, withdrawal…"
              className="pl-8"
            />
          </div>
        )}
      </Field>
      <Button type="submit" variant="secondary">
        Search
      </Button>
    </form>
  );
}

/**
 * Find a person or a record by name and filter on it.
 *
 * One kind at a time, a few letters, a short list. Picking an answer sets the
 * filter the server said it feeds and clears the other two, because "about
 * this consent record" and "about this person" are different questions and
 * stacking them silently answers neither.
 */
function AboutPicker({
  vocabulary,
  onPick,
}: {
  vocabulary: AuditVocabulary | undefined;
  onPick: (next: Partial<AuditFilterState>) => void;
}) {
  const kinds = vocabulary?.lookups ?? [];
  const [kind, setKind] = React.useState("");
  const [typed, setTyped] = React.useState("");
  const [debounced, setDebounced] = React.useState("");
  const [open, setOpen] = React.useState(false);
  const listId = React.useId();

  React.useEffect(() => {
    const handle = setTimeout(() => setDebounced(typed.trim()), 250);
    return () => clearTimeout(handle);
  }, [typed]);

  const effectiveKind = kind || kinds[0]?.kind || "";
  const lookup = useAuditLookup(effectiveKind, debounced, open && debounced.length > 0);

  function pick(hit: AuditLookupHit) {
    const cleared = {
      subject: "",
      actor: "",
      entity: "",
      entity_type: "",
      label: hit.label,
    };
    if (hit.filter === "subject") onPick({ ...cleared, subject: hit.uuid });
    else if (hit.filter === "actor") onPick({ ...cleared, actor: hit.uuid });
    else onPick({ ...cleared, entity: hit.uuid, entity_type: hit.entity_type });
    setTyped("");
    setOpen(false);
  }

  return (
    <div className="flex items-end gap-2">
      <Field label="About">
        {(p) => (
          <Select
            {...p}
            className="w-44"
            value={effectiveKind}
            onChange={(e) => setKind(e.target.value)}
          >
            {kinds.map((k) => (
              <option key={k.kind} value={k.kind}>
                {k.label}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <div className="relative">
        <Field label="Name">
          {(p) => (
            <Input
              {...p}
              role="combobox"
              aria-expanded={open}
              aria-controls={listId}
              aria-autocomplete="list"
              className="w-64"
              value={typed}
              placeholder="Type a few letters"
              onChange={(e) => {
                setTyped(e.target.value);
                setOpen(true);
              }}
              onFocus={() => setOpen(true)}
              onBlur={() => setTimeout(() => setOpen(false), 150)}
            />
          )}
        </Field>
        {open && debounced && (
          <ul
            id={listId}
            role="listbox"
            className="absolute z-20 mt-1 max-h-72 w-96 overflow-auto rounded-lg border border-border bg-surface p-1 shadow-[var(--shadow-md)]"
          >
            {lookup.isLoading && (
              <li className="px-2 py-1.5 text-sm text-text-subtle">Looking…</li>
            )}
            {lookup.data?.length === 0 && (
              <li className="px-2 py-1.5 text-sm text-text-subtle">
                Nothing by that name.
              </li>
            )}
            {(lookup.data ?? []).map((hit) => (
              <li key={hit.uuid} role="option" aria-selected={false}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => pick(hit)}
                  className="flex w-full flex-col items-start rounded-md px-2 py-1.5 text-left hover:bg-bg-inset"
                >
                  <span className="text-sm">{hit.label}</span>
                  {hit.hint && <span className="text-xs text-text-subtle">{hit.hint}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** The chips: which filters are on, in words a person would use. */
export function describeFilters(
  f: AuditFilterState,
  vocabulary: AuditVocabulary | undefined,
  clear: (keys: (keyof AuditFilterState)[]) => void,
): { label: string; value: string; onClear: () => void }[] {
  const chips: { label: string; value: string; onClear: () => void }[] = [];
  const nounOf = (t: string) =>
    vocabulary?.entity_types.find((e) => e.value === t)?.label ?? humanise(t);
  if (f.q) chips.push({ label: "Search", value: f.q, onClear: () => clear(["q"]) });
  if (f.subject)
    chips.push({
      label: "Data principal",
      value: f.label || f.subject.slice(0, 8),
      onClear: () => clear(["subject", "label"]),
    });
  if (f.actor)
    chips.push({
      label: "Actor",
      value: f.label || f.actor.slice(0, 8),
      onClear: () => clear(["actor", "label"]),
    });
  if (f.entity && f.entity_type)
    chips.push({
      label: nounOf(f.entity_type),
      value: f.label || f.entity.slice(0, 8),
      onClear: () => clear(["entity", "entity_type", "label"]),
    });
  else if (f.entity_type)
    chips.push({
      label: "Record type",
      value: nounOf(f.entity_type),
      onClear: () => clear(["entity_type"]),
    });
  if (f.event_type)
    chips.push({
      label: "Event",
      value:
        vocabulary?.event_types.find((e) => e.value === f.event_type)?.label ??
        f.event_type,
      onClear: () => clear(["event_type"]),
    });
  else if (f.event_group)
    chips.push({
      label: "Area",
      value:
        vocabulary?.event_groups.find((g) => g.value === f.event_group)?.label ??
        f.event_group,
      onClear: () => clear(["event_group"]),
    });
  if (f.actor_role)
    chips.push({
      label: "Actor role",
      value: humanise(f.actor_role),
      onClear: () => clear(["actor_role"]),
    });
  if (f.from) chips.push({ label: "From", value: f.from, onClear: () => clear(["from"]) });
  if (f.to) chips.push({ label: "To", value: f.to, onClear: () => clear(["to"]) });
  return chips;
}

export { X as ClearIcon };
