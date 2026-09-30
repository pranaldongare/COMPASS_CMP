/**
 * Who a breach touched (S3-02).
 *
 * Rule 7(1) asks for a notice to each affected principal, to the best of the
 * fiduciary's knowledge. The server derives the people from where the breach
 * happened - a processor's exports, a source's assets, the platform's own
 * tables in a window - and the DPO confirms it, leaving out whom the records
 * wrongly include and adding whom they cannot show. Each confirmation is a
 * revision; nobody listed is ever removed, and each newly listed person is
 * notified in turn.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Trash2, UserPlus, Users } from "lucide-react";
import * as React from "react";

import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Select,
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { lookupAudit } from "@/features/audit/api";
import { confirmAffected, listAffected, previewAffected } from "@/features/breach/api";
import {
  ProcessorPicker,
  SourcePicker,
  instant,
  messageOf,
} from "@/features/breach/components/record-breach";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type {
  AuditLookupHit,
  Breach,
  BreachAffected,
  BreachPerson,
  BreachPreview,
  BreachScope,
  BreachScopeKind,
} from "@/types";

const FOUND_BY: Record<BreachPerson["found_by"], string> = {
  processor: "Exported to the processor",
  data_source: "In the source's assets",
  platform: "In the platform's tables",
  dpo: "Added by the DPO",
};

/** A scope being edited: the window as `datetime-local` text until it is sent. */
interface Draft {
  kind: BreachScopeKind;
  processor_uuid: string;
  source_uuid: string;
  tables: string[];
  since: string;
  until: string;
}

function fromLocation(breach: Breach): Draft {
  const l = breach.location;
  const kind: BreachScopeKind =
    l.kind === "processor" ? "processor" : l.kind === "data_source" ? "data_source" : "platform";
  return {
    kind,
    processor_uuid: l.processor_uuid ?? "",
    source_uuid: l.source_uuid ?? "",
    // None ticked: which tables were exposed is the DPO's to say, and "all of
    // them since the beginning" is everybody on the platform.
    tables: [],
    since: "",
    until: "",
  };
}

function toScope(d: Draft): BreachScope {
  if (d.kind === "processor") return { kind: d.kind, processor_uuid: d.processor_uuid };
  if (d.kind === "data_source") return { kind: d.kind, source_uuid: d.source_uuid };
  return { kind: d.kind, tables: d.tables, since: instant(d.since), until: instant(d.until) };
}

function ready(d: Draft): boolean {
  if (d.kind === "processor") return d.processor_uuid !== "";
  if (d.kind === "data_source") return d.source_uuid !== "";
  return d.tables.length > 0;
}

function ScopeEditor({
  draft,
  tables,
  onChange,
  onRemove,
}: {
  draft: Draft;
  tables: string[];
  onChange: (d: Draft) => void;
  onRemove: () => void;
}) {
  return (
    <div className="space-y-3 rounded-md border border-border p-3">
      <div className="flex items-end gap-2">
        <Field label="Look in">
          {(p) => (
            <Select
              {...p}
              value={draft.kind}
              onChange={(e) => onChange({ ...draft, kind: e.target.value as BreachScopeKind })}
            >
              <option value="processor">Files exported to a processor</option>
              <option value="data_source">Assets a data source captured</option>
              <option value="platform">The platform&apos;s own tables</option>
            </Select>
          )}
        </Field>
        <Button variant="ghost" size="sm" aria-label="Remove this place" onClick={onRemove}>
          <Trash2 className="size-4" />
        </Button>
      </div>
      {draft.kind === "processor" && (
        <ProcessorPicker value={draft.processor_uuid} onChange={(v) => onChange({ ...draft, processor_uuid: v })} />
      )}
      {draft.kind === "data_source" && (
        <SourcePicker value={draft.source_uuid} onChange={(v) => onChange({ ...draft, source_uuid: v })} />
      )}
      {draft.kind === "platform" && (
        <>
          <fieldset>
            <legend className="text-sm font-medium">Affected tables</legend>
            <div className="mt-1 grid gap-1 sm:grid-cols-3">
              {tables.map((t) => (
                <label key={t} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={draft.tables.includes(t)}
                    onChange={(e) =>
                      onChange({
                        ...draft,
                        tables: e.target.checked ? [...draft.tables, t] : draft.tables.filter((x) => x !== t),
                      })
                    }
                  />
                  <span className="font-mono text-xs">{t}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Rows written from" hint="Empty: from the beginning">
              {(p) => (
                <Input {...p} type="datetime-local" value={draft.since} onChange={(e) => onChange({ ...draft, since: e.target.value })} />
              )}
            </Field>
            <Field label="Rows written until" hint="Empty: until now">
              {(p) => (
                <Input {...p} type="datetime-local" value={draft.until} onChange={(e) => onChange({ ...draft, until: e.target.value })} />
              )}
            </Field>
          </div>
        </>
      )}
    </div>
  );
}

/** Find a person the records cannot show, by contact or part of a name. */
function AddByHand({ added, onAdd }: { added: AuditLookupHit[]; onAdd: (hit: AuditLookupHit) => void }) {
  const [q, setQ] = React.useState("");
  const [hits, setHits] = React.useState<AuditLookupHit[]>([]);
  const [busy, setBusy] = React.useState(false);
  async function find() {
    setBusy(true);
    try {
      const [people, staff] = await Promise.all([lookupAudit("data_subject", q), lookupAudit("staff", q)]);
      setHits([...people, ...staff]);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="space-y-2">
      <div className="flex items-end gap-2">
        <Field label="Add someone the records cannot show" hint="An email, a mobile, or part of a name">
          {(p) => <Input {...p} value={q} onChange={(e) => setQ(e.target.value)} />}
        </Field>
        <Button variant="secondary" size="sm" disabled={q.trim().length < 3} loading={busy} onClick={find}>
          <Search className="size-4" />
          Find
        </Button>
      </div>
      {hits.length > 0 && (
        <ul className="divide-y divide-border rounded-md border border-border text-sm">
          {hits.map((h) => (
            <li key={h.uuid} className="flex items-center justify-between gap-2 px-3 py-2">
              <span>
                {h.label}
                {h.hint && <span className="ml-2 text-xs text-text-subtle">{h.hint}</span>}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={added.some((a) => a.uuid === h.uuid)}
                onClick={() => onAdd(h)}
              >
                <UserPlus className="size-4" />
                Add
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Revise({ breach, tables, onDone }: { breach: Breach; tables: string[]; onDone: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [drafts, setDrafts] = React.useState<Draft[]>(() => [fromLocation(breach)]);
  const [preview, setPreview] = React.useState<BreachPreview | null>(null);
  const [exclude, setExclude] = React.useState<string[]>([]);
  const [added, setAdded] = React.useState<AuditLookupHit[]>([]);
  const [note, setNote] = React.useState("");
  const look = useMutation({ mutationFn: (s: BreachScope[]) => previewAffected(breach.breach_uuid, s) });
  const save = useMutation({
    mutationFn: () =>
      confirmAffected(breach.breach_uuid, {
        scopes: drafts.map(toScope),
        exclude,
        add: added.map((a) => a.uuid),
        note: note.trim() || null,
      }),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.affected(breach.breach_uuid), fresh);
      void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
    },
  });
  const scopesReady = drafts.length > 0 && drafts.every(ready);

  async function show() {
    try {
      setPreview(await look.mutateAsync(drafts.map(toScope)));
      setExclude([]);
    } catch (err) {
      toast.error("Could not derive", messageOf(err, "The server refused."));
    }
  }

  async function confirm() {
    try {
      const fresh = await save.mutateAsync();
      const [last] = fresh.revisions.slice(-1);
      toast.success(
        `Revision ${last?.revision ?? ""} confirmed`,
        `${last?.newly_listed ?? 0} newly listed; ${fresh.total} in all.`,
      );
      onDone();
    } catch (err) {
      toast.error("Not confirmed", messageOf(err, "The server refused."));
    }
  }

  return (
    <div className="space-y-4 border-t border-border pt-4">
      {drafts.map((d, i) => (
        <ScopeEditor
          key={i}
          draft={d}
          tables={tables}
          onChange={(next) => {
            setDrafts(drafts.map((x, j) => (j === i ? next : x)));
            setPreview(null);
          }}
          onRemove={() => {
            setDrafts(drafts.filter((_, j) => j !== i));
            setPreview(null);
          }}
        />
      ))}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setDrafts([...drafts, { kind: "platform", processor_uuid: "", source_uuid: "", tables: [], since: "", until: "" }])}
        >
          <Plus className="size-4" />
          Another place to look
        </Button>
        <Button variant="secondary" size="sm" disabled={!scopesReady} loading={look.isPending} onClick={show}>
          <Search className="size-4" />
          Show what the records say
        </Button>
      </div>

      {preview && (
        <div className="space-y-2">
          <p className="text-sm">
            The records place <strong>{preview.derived}</strong> people here: {preview.would_add} not yet listed,{" "}
            {preview.already_listed} already listed.
            {preview.derived > preview.people.length && ` The first ${preview.people.length} are shown.`}
          </p>
          {preview.people.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Person</Th>
                  <Th>Found</Th>
                  <Th>Leave out</Th>
                </tr>
              </thead>
              <tbody>
                {preview.people.map((p) => (
                  <Tr key={p.person_uuid}>
                    <Td>
                      {p.full_name ?? "No name"}
                      {p.already_listed && <Badge className="ml-2">Listed</Badge>}
                    </Td>
                    <Td className="text-sm">{FOUND_BY[p.found_by]}</Td>
                    <Td>
                      <input
                        type="checkbox"
                        aria-label={`Leave out ${p.full_name ?? "this person"}`}
                        disabled={p.already_listed}
                        checked={exclude.includes(p.person_uuid)}
                        onChange={(e) =>
                          setExclude(
                            e.target.checked
                              ? [...exclude, p.person_uuid]
                              : exclude.filter((u) => u !== p.person_uuid),
                          )
                        }
                      />
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
      )}

      <AddByHand added={added} onAdd={(h) => setAdded([...added, h])} />
      {added.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {added.map((a) => (
            <li key={a.uuid}>
              <Badge tone="accent">
                {a.label}
                <button
                  type="button"
                  className="ml-1"
                  aria-label={`Remove ${a.label}`}
                  onClick={() => setAdded(added.filter((x) => x.uuid !== a.uuid))}
                >
                  ×
                </button>
              </Badge>
            </li>
          ))}
        </ul>
      )}
      <Field label="Note" hint="Optional: what this revision is based on">
        {(p) => <Textarea {...p} value={note} onChange={(e) => setNote(e.target.value)} />}
      </Field>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button
          variant="primary"
          disabled={!(scopesReady || added.length > 0)}
          loading={save.isPending}
          onClick={confirm}
        >
          Confirm the list
        </Button>
      </div>
    </div>
  );
}

export function AffectedCard({ breach }: { breach: Breach }) {
  const qc = useQueryClient();
  const query = useQuery<BreachAffected>({
    queryKey: keys.breach.affected(breach.breach_uuid),
    queryFn: () => listAffected(breach.breach_uuid),
  });
  const [revising, setRevising] = React.useState(false);
  const data = query.data;
  // Pages beyond the first belong to the listing they were read from; a fresh
  // listing (a new revision) starts from its own first page again.
  const [extra, setExtra] = React.useState<{
    from: BreachAffected | undefined;
    people: BreachAffected["people"];
    cursor: string | null;
  }>({ from: undefined, people: [], cursor: null });
  const paging = extra.from === data ? extra : { from: data, people: [], cursor: data?.next_cursor ?? null };
  const cursor = paging.cursor;

  async function loadMore() {
    if (!cursor) return;
    const page = await listAffected(breach.breach_uuid, cursor);
    setExtra({ from: data, people: [...paging.people, ...page.people], cursor: page.next_cursor });
  }

  const people = [...(data?.people ?? []), ...paging.people];
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Users className="mr-2 inline size-4" aria-hidden="true" />
          Who it touched
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Rule 7(1): every affected Data Principal, to the best of current knowledge. Derived from the records, confirmed
          by you, and revised as knowledge grows. Nobody listed is removed; each newly listed person is notified.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {data && data.revisions.length > 0 ? (
          <>
            <p className="text-sm">
              <strong>{data.total}</strong> listed across {data.revisions.length} revision
              {data.revisions.length === 1 ? "" : "s"}.
            </p>
            <ol className="space-y-1 text-xs text-text-muted">
              {data.revisions.map((r) => (
                <li key={r.revision_uuid}>
                  Revision {r.revision}, {formatDateTime(r.confirmed_at)} by {r.confirmed_by_name ?? "unknown"}: derived{" "}
                  {r.derived}, left out {r.excluded}, added by hand {r.added_by_hand}, newly listed {r.newly_listed}
                  {r.note && <span className="block whitespace-pre-wrap text-text">{r.note}</span>}
                </li>
              ))}
            </ol>
            <Table>
              <thead>
                <tr>
                  <Th>Person</Th>
                  <Th>How found</Th>
                  <Th>Reachable by</Th>
                  <Th>Revision</Th>
                </tr>
              </thead>
              <tbody>
                {people.map((p) => (
                  <Tr key={p.affected_uuid}>
                    <Td>{p.full_name ?? "No name"}</Td>
                    <Td className="text-sm">{FOUND_BY[p.found_by]}</Td>
                    <Td className="text-sm">
                      {[p.has_email && "email", p.has_mobile && "SMS", "their account"].filter(Boolean).join(", ")}
                    </Td>
                    <Td className="text-sm">{p.revision}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
            {cursor && (
              <Button variant="ghost" size="sm" onClick={loadMore}>
                Show more
              </Button>
            )}
          </>
        ) : (
          <p className="text-sm text-text-muted">{query.isLoading ? "Loading…" : "Nobody confirmed yet."}</p>
        )}
        {breach.status === "open" && !revising && data && (
          <Button variant="secondary" size="sm" onClick={() => setRevising(true)}>
            <Users className="size-4" />
            {data.revisions.length ? "Revise the list" : "Derive who it touched"}
          </Button>
        )}
        {revising && data && (
          <Revise
            breach={breach}
            tables={data.platform_tables}
            onDone={() => {
              setRevising(false);
              void qc.invalidateQueries({ queryKey: keys.breach.affected(breach.breach_uuid) });
            }}
          />
        )}
      </CardBody>
    </Card>
  );
}
