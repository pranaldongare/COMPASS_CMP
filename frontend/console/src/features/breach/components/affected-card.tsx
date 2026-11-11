/**
 * The people a breach affected (S3-02, reworked 2026-11-06).
 *
 * Rule 7(1) asks for a notice to each affected principal, to the best of the
 * fiduciary's knowledge. Whoever runs a breach knows what it reached in the
 * words of the work, so that is what this asks: a project or activity, a
 * vendor, a data source, a list from outside, or people typed in by mail ID
 * or mobile number, on the platform or not (2026-11-11). Database tables
 * are no longer a way to look: nobody running a breach could say which ones
 * it reached. The server finds the people; the office reads who was found,
 * unticks anyone wrong, and adds the rest. Each addition is a revision
 * underneath. Nobody listed is ever removed, and anyone listed later is
 * reached when the notice is next sent.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Database,
  FileSpreadsheet,
  FolderKanban,
  Search,
  UserPlus,
  Users,
  type LucideIcon,
} from "lucide-react";
import * as React from "react";

import { FormError } from "@/components/forms";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
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
import {
  affectedOptions,
  checkBreachTyped,
  confirmAffected,
  listAffected,
  listBreachContacts,
  previewAffected,
  takeBreachTyped,
} from "@/features/breach/api";
import { BreachContacts, Counts, NEXT_STEP, UploadList } from "@/features/breach/components/breach-lists";
import {
  ProcessorPicker,
  SourcePicker,
  instant,
  messageOf,
} from "@/features/breach/components/record-breach";
import { formatDate, formatDateTime } from "@/lib/format";
import { canSee } from "@/lib/permissions";
import { keys } from "@/lib/query";
import { useAuth, useToast } from "@/providers";
import { todayLocal } from "@/lib/dates";
import type {
  AuditLookupHit,
  Breach,
  BreachAffected,
  BreachAffectedRevision,
  BreachListReport,
  BreachPerson,
  BreachPreview,
  BreachScope,
  BreachScopeKind,
  BreachTyped,
} from "@/types";

const FOUND_BY: Record<BreachPerson["found_by"], string> = {
  project: "In a project or activity",
  processor: "Sent to a vendor",
  data_source: "In a data source",
  dpo: "Added by hand",
  upload: "In a list sent to us",
  platform: "From the platform's records",
};

type Way = BreachScopeKind | "upload" | "typed";

const WAYS: { way: Way; label: string; hint?: string; icon: LucideIcon }[] = [
  {
    way: "project",
    label: "From a project or activity",
    hint: "Everyone who gave consent in it, including those who later withdrew. Optional: only between two dates.",
    icon: FolderKanban,
  },
  { way: "processor", label: "From a vendor", hint: "Everyone whose data we sent to them.", icon: Building2 },
  { way: "data_source", label: "From a data source", hint: "Everyone recorded in its files.", icon: Database },
  { way: "upload", label: "Upload an Excel list", hint: "Name, Mail ID, Mobile number.", icon: FileSpreadsheet },
  {
    way: "typed",
    label: "Add by mail ID or mobile number",
    hint: "Many at once, separated by commas, on the platform or not. Or find someone on the platform by name.",
    icon: UserPlus,
  },
];

const headcount = (n: number) => `${n} ${n === 1 ? "person" : "people"}`;

/** What is being chosen: the dates as `date` input text until they are sent. */
interface Draft {
  project_uuid: string;
  processor_uuid: string;
  source_uuid: string;
  from: string;
  until: string;
}

const backwards = (d: Draft) => d.from !== "" && d.until !== "" && d.until < d.from;

function toScope(kind: BreachScopeKind, d: Draft): BreachScope {
  if (kind === "processor") return { kind, processor_uuid: d.processor_uuid };
  if (kind === "data_source") return { kind, source_uuid: d.source_uuid };
  return {
    kind,
    project_uuid: d.project_uuid,
    // Whole days, where the person is: "until the 6th" takes in the 6th.
    since: d.from ? instant(`${d.from}T00:00`) : null,
    until: d.until ? instant(`${d.until}T23:59:59.999`) : null,
  };
}

function ready(kind: BreachScopeKind, d: Draft): boolean {
  if (kind === "processor") return d.processor_uuid !== "";
  if (kind === "data_source") return d.source_uuid !== "";
  return d.project_uuid !== "" && !backwards(d);
}

function period(scope: Record<string, unknown>): string {
  const since = scope.since ? formatDate(String(scope.since)) : null;
  const until = scope.until ? formatDate(String(scope.until)) : null;
  if (since && until) return `, consent given ${since} to ${until}`;
  if (since) return `, consent given from ${since}`;
  return until ? `, consent given until ${until}` : "";
}

/** Where people were found, as the person chose it. A name can be missing: a
 *  row from before 2026-11-06 kept only the uuid. */
function placeOf(scope: Record<string, unknown>): string {
  switch (scope.kind) {
    case "project":
      return `From ${String(scope.project_name ?? "a project or activity")}${period(scope)}`;
    case "processor":
      return `Sent to ${String(scope.processor_name ?? "a vendor")}`;
    case "data_source":
      return `In ${String(scope.source_name ?? "a data source")}`;
    case "upload":
      if (scope.file === "typed") return "Typed in by mail ID or mobile number";
      return scope.file === "assets" ? "From a list of asset IDs" : "From a list of people";
    default:
      // Listed when tables were still a way to look. Their names mean
      // nothing here.
      return "From the platform's records";
  }
}

function history(r: BreachAffectedRevision): string {
  const added = headcount(r.newly_listed);
  if (r.scopes.length === 0) return `${added} added by hand.`;
  // A list's people with no account are kept apart, under Lists taken.
  const who = r.scopes.some((s) => s.kind === "upload") ? `${added} on the platform` : added;
  return `${r.scopes.map(placeOf).join("; ")}. ${who} added${r.excluded ? `, ${r.excluded} left out` : ""}.`;
}

/** Add to the list, refresh what hangs off it, and say what comes next. */
function useAddToList(breach: Breach, onDone: () => void) {
  const toast = useToast();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof confirmAffected>[1]) => confirmAffected(breach.breach_uuid, body),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.affected(breach.breach_uuid), fresh);
      void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
      toast.success(`${headcount(fresh.revisions.at(-1)?.newly_listed ?? 0)} added to the list`, NEXT_STEP);
      onDone();
    },
    onError: (err) => toast.error("Not added", messageOf(err, "The server refused.")),
  });
}

/** Find a person the records cannot show, by contact or part of a name. */
function AddByHand({ added, onAdd }: { added: AuditLookupHit[]; onAdd: (hit: AuditLookupHit) => void }) {
  const toast = useToast();
  const [q, setQ] = React.useState("");
  const [hits, setHits] = React.useState<AuditLookupHit[] | null>(null);
  const [busy, setBusy] = React.useState(false);
  async function find() {
    setBusy(true);
    try {
      const [people, staff] = await Promise.all([lookupAudit("data_subject", q), lookupAudit("staff", q)]);
      setHits([...people, ...staff]);
    } catch (err) {
      toast.error("Could not search", messageOf(err, "The server refused."));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="space-y-2">
      <div className="flex items-end gap-2">
        <Field label="Find the person" hint="A mail ID, a mobile number, or part of a name">
          {(p) => <Input {...p} value={q} onChange={(e) => setQ(e.target.value)} />}
        </Field>
        <Button variant="secondary" size="sm" disabled={q.trim().length < 3} loading={busy} onClick={find}>
          <Search className="size-4" />
          Find
        </Button>
      </div>
      {hits?.length === 0 && (
        <p className="text-sm text-text-muted">
          Nobody on the platform found. Someone who is not on it is added by their mail ID or mobile number above.
        </p>
      )}
      {hits && hits.length > 0 && (
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

/** Mail IDs and mobile numbers typed in, many at once and on the platform or
 *  not (2026-11-11), and anybody on the platform found by name. Checked
 *  first, as a list is: nothing is written until it is added. */
function AddTyped({ breach, onBack, onDone }: { breach: Breach; onBack: () => void; onDone: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [mailIds, setMailIds] = React.useState("");
  const [mobiles, setMobiles] = React.useState("");
  const [picked, setPicked] = React.useState<AuditLookupHit[]>([]);
  const [note, setNote] = React.useState("");
  const [report, setReport] = React.useState<BreachListReport | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<"check" | "take" | null>(null);
  const body = (): BreachTyped => ({
    mail_ids: mailIds,
    mobiles,
    people: picked.map((p) => p.uuid),
    note: note.trim() || null,
  });
  const anything = mailIds.trim() !== "" || mobiles.trim() !== "" || picked.length > 0;

  // What is added is what was checked: any change asks for a fresh check.
  function changed() {
    setReport(null);
    setError(null);
  }

  async function check() {
    setBusy("check");
    changed();
    try {
      setReport(await checkBreachTyped(breach.breach_uuid, body()));
    } catch (err) {
      setError(messageOf(err, "These could not be checked."));
    } finally {
      setBusy(null);
    }
  }

  async function take() {
    setBusy("take");
    setError(null);
    try {
      const taken = await takeBreachTyped(breach.breach_uuid, body());
      toast.success(`${headcount(taken.matched_people + taken.new_contacts)} added to the list`, NEXT_STEP);
      void qc.invalidateQueries({ queryKey: keys.breach.affected(breach.breach_uuid) });
      void qc.invalidateQueries({ queryKey: keys.breach.notices(breach.breach_uuid) });
      void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
      onDone();
    } catch (err) {
      setError(messageOf(err, "They were not added."));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-medium">Add by mail ID or mobile number</p>
        <p className="mt-0.5 text-xs text-text-muted">
          Each mail ID and each mobile number is one person. Someone on the platform is matched and listed as
          themselves; anyone else is kept as a contact of this breach and told by email or SMS.
        </p>
      </div>
      <Field
        label="Mail IDs"
        hint="Separated by commas. Pasting from Outlook works too: Meera Nair <meera@example.com>; …"
      >
        {(p) => (
          <Textarea
            {...p}
            rows={3}
            value={mailIds}
            onChange={(e) => {
              setMailIds(e.target.value);
              changed();
            }}
          />
        )}
      </Field>
      <Field label="Mobile numbers" hint="Separated by commas, each with its country code: +91 98765 43210">
        {(p) => (
          <Textarea
            {...p}
            rows={2}
            value={mobiles}
            onChange={(e) => {
              setMobiles(e.target.value);
              changed();
            }}
          />
        )}
      </Field>
      <details open={picked.length > 0}>
        <summary className="cursor-pointer text-xs text-text-muted">
          Know only their name? Find them on the platform
        </summary>
        <div className="mt-2">
          <AddByHand
            added={picked}
            onAdd={(h) => {
              setPicked([...picked, h]);
              changed();
            }}
          />
        </div>
      </details>
      {picked.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {picked.map((a) => (
            <li key={a.uuid}>
              <Badge tone="accent">
                {a.label}
                <button
                  type="button"
                  className="ml-1"
                  aria-label={`Remove ${a.label}`}
                  onClick={() => {
                    setPicked(picked.filter((x) => x.uuid !== a.uuid));
                    changed();
                  }}
                >
                  ×
                </button>
              </Badge>
            </li>
          ))}
        </ul>
      )}
      <Field label="Note" hint="Optional: why they are being added">
        {(p) => <Textarea {...p} value={note} onChange={(e) => setNote(e.target.value)} />}
      </Field>

      <FormError message={error} />

      {report && (
        <div className="space-y-3 rounded-md bg-bg-inset p-3">
          <Counts report={report} taken={false} />
          {report.errors.length > 0 && (
            <div>
              <p className="text-sm font-medium text-warning-text">Could not be used ({report.unreadable})</p>
              <ul className="mt-1 max-h-48 space-y-0.5 overflow-y-auto text-xs">
                {report.errors.map((e) => (
                  <li key={`${e.row}:${e.message}`}>{e.message}</li>
                ))}
                {report.more_errors > 0 && <li>…and {report.more_errors} more</li>}
              </ul>
            </div>
          )}
          {report.would_add === 0 ? (
            <Alert tone="warning">
              <p className="text-sm">
                Nobody here would be added
                {report.already_listed ? ": everybody is already listed." : "."}
              </p>
            </Alert>
          ) : (
            report.unreadable > 0 && (
              <p className="text-xs text-text-muted">
                Adding takes the ones that can be used. Correct the others and add them after.
              </p>
            )
          )}
        </div>
      )}

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onBack}>
          Back
        </Button>
        <Button variant="secondary" disabled={!anything} loading={busy === "check"} onClick={check}>
          Check
        </Button>
        <Button
          variant="primary"
          disabled={!report || report.would_add === 0}
          loading={busy === "take"}
          onClick={take}
        >
          <UserPlus className="size-4" />
          {report && report.would_add > 0 ? `Add ${headcount(report.would_add)}` : "Add to the list"}
        </Button>
      </div>
    </div>
  );
}

/** Only those with people in them, each with how many; the server's answer. */
function ProjectChoice({
  breach,
  draft,
  onChange,
  onUpload,
}: {
  breach: Breach;
  draft: Draft;
  onChange: (d: Draft) => void;
  onUpload: () => void;
}) {
  const query = useQuery({
    queryKey: keys.breach.affectedOptions(breach.breach_uuid),
    queryFn: () => affectedOptions(breach.breach_uuid),
  });
  if (query.isLoading) return <p className="text-sm text-text-muted">Loading…</p>;
  const projects = query.data?.projects ?? [];
  if (query.isError) {
    return <Alert tone="danger">{messageOf(query.error, "The projects could not be loaded.")}</Alert>;
  }
  if (projects.length === 0) {
    return (
      <Alert tone="info" title="No project or activity has people in it yet">
        <p>If you know who was affected, upload an Excel list instead.</p>
        <Button variant="secondary" size="sm" className="mt-2" onClick={onUpload}>
          <FileSpreadsheet className="size-4" />
          Upload an Excel list
        </Button>
      </Alert>
    );
  }
  return (
    <div className="space-y-3">
      <Field label="Project or activity" required>
        {(p) => (
          <Select
            {...p}
            value={draft.project_uuid}
            onChange={(e) => onChange({ ...draft, project_uuid: e.target.value })}
          >
            <option value="">Choose…</option>
            {projects.map((o) => (
              <option key={o.project_uuid} value={o.project_uuid}>
                {`${o.project_name} · ${o.is_activity ? "Activity" : "Project"} · ${headcount(o.people)}`}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Consent given from" hint="Optional">
          {(p) => (
            <Input
              {...p}
              type="date"
              value={draft.from}
              max={draft.until || todayLocal()}
              onChange={(e) => onChange({ ...draft, from: e.target.value })}
            />
          )}
        </Field>
        <Field
          label="Consent given until"
          hint="Optional"
          error={backwards(draft) ? "This is before the first date" : undefined}
        >
          {(p) => (
            <Input
              {...p}
              type="date"
              value={draft.until}
              min={draft.from || undefined}
              max={todayLocal()}
              onChange={(e) => onChange({ ...draft, until: e.target.value })}
            />
          )}
        </Field>
      </div>
    </div>
  );
}

/** Who was found: anyone wrong is unticked, and the rest are added. */
function Review({
  breach,
  scope,
  preview,
  onBack,
  onDone,
}: {
  breach: Breach;
  scope: BreachScope;
  preview: BreachPreview;
  onBack: () => void;
  onDone: () => void;
}) {
  const save = useAddToList(breach, onDone);
  const [unticked, setUnticked] = React.useState<string[]>([]);
  const [note, setNote] = React.useState("");
  const adding = preview.would_add - unticked.length;
  const people = [...preview.people].sort((a, b) =>
    (a.full_name ?? "").localeCompare(b.full_name ?? "", undefined, { sensitivity: "base" }),
  );
  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-medium">{headcount(preview.derived)} found</p>
        <p className="mt-0.5 text-xs text-text-muted">
          {preview.scopes.map(placeOf).join("; ")}. {preview.already_listed} already listed.
        </p>
      </div>
      {preview.derived === 0 && (
        <Alert tone="info">Nobody is recorded here. Go back and choose another, or upload an Excel list.</Alert>
      )}
      {preview.derived > 0 && preview.would_add === 0 && (
        <Alert tone="info">Everyone found is already on the list.</Alert>
      )}
      {people.length > 0 && (
        <div className="space-y-1.5">
          {preview.would_add > 0 && <p className="text-xs text-text-muted">Untick anyone who should not be on the list.</p>}
          {preview.derived > people.length && (
            <p className="text-xs text-text-muted">
              The first {people.length} of {preview.derived} are shown, so only they can be unticked. Everyone else found
              is added too.
            </p>
          )}
          <ul className="max-h-72 divide-y divide-border overflow-y-auto rounded-md border border-border text-sm">
            {people.map((p) => (
              <li key={p.person_uuid}>
                <label className="flex items-center gap-2 px-3 py-2">
                  <input
                    type="checkbox"
                    className="size-4 accent-[var(--accent)]"
                    // Listed stays listed: there is nothing to untick.
                    disabled={p.already_listed}
                    checked={!unticked.includes(p.person_uuid)}
                    onChange={(e) =>
                      setUnticked(
                        e.target.checked
                          ? unticked.filter((u) => u !== p.person_uuid)
                          : [...unticked, p.person_uuid],
                      )
                    }
                  />
                  <span className="min-w-0 flex-1">{p.full_name ?? "No name"}</span>
                  {p.already_listed && <Badge>Already listed</Badge>}
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Field label="Note" hint="Optional: what this is based on">
        {(p) => <Textarea {...p} value={note} onChange={(e) => setNote(e.target.value)} />}
      </Field>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onBack}>
          Back
        </Button>
        <Button
          variant="primary"
          disabled={adding <= 0}
          loading={save.isPending}
          onClick={() =>
            save.mutate({ scopes: [scope], exclude: unticked, add: [], note: note.trim() || null })
          }
        >
          Add {headcount(adding)}
        </Button>
      </div>
    </div>
  );
}

function AddPeople({ breach, onClose }: { breach: Breach; onClose: () => void }) {
  const { me } = useAuth();
  const toast = useToast();
  const [way, setWay] = React.useState<Way | null>(null);
  const [found, setFound] = React.useState<BreachPreview | null>(null);
  // Where the incident happened is the likeliest answer, so it starts chosen.
  const [draft, setDraft] = React.useState<Draft>({
    project_uuid: "",
    processor_uuid: breach.location.processor_uuid ?? "",
    source_uuid: breach.location.source_uuid ?? "",
    from: "",
    until: "",
  });
  const look = useMutation({ mutationFn: (s: BreachScope) => previewAffected(breach.breach_uuid, [s]) });

  async function find(kind: BreachScopeKind) {
    try {
      setFound(await look.mutateAsync(toScope(kind, draft)));
    } catch (err) {
      toast.error("Could not find the people", messageOf(err, "The server refused."));
    }
  }

  // The Legal PoC has no sources section, so nothing to choose from.
  const ways = WAYS.filter((w) => w.way !== "data_source" || canSee(me, "sources"));
  const chosen = WAYS.find((w) => w.way === way);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        size="lg"
        title="Add people"
        description="Adding someone tells them nothing. They hear only when the notice is sent."
      >
        {way === null ? (
          <div className="space-y-3" role="group" aria-labelledby="add-people-how">
            <p id="add-people-how" className="text-sm font-medium">
              How do you want to add people?
            </p>
            {ways.map((w) => (
              <button
                key={w.way}
                type="button"
                className="flex w-full items-start gap-3 rounded-lg border border-border p-3 text-left transition-colors hover:bg-bg-inset"
                onClick={() => setWay(w.way)}
              >
                <w.icon className="mt-0.5 size-4 shrink-0 text-text-subtle" aria-hidden="true" />
                <span>
                  <span className="block text-sm font-medium">{w.label}</span>
                  {w.hint && <span className="mt-0.5 block text-xs text-text-muted">{w.hint}</span>}
                </span>
              </button>
            ))}
          </div>
        ) : way === "upload" ? (
          <UploadList breach={breach} onBack={() => setWay(null)} onDone={onClose} />
        ) : way === "typed" ? (
          <AddTyped breach={breach} onBack={() => setWay(null)} onDone={onClose} />
        ) : found ? (
          <Review
            breach={breach}
            scope={toScope(way, draft)}
            preview={found}
            onBack={() => setFound(null)}
            onDone={onClose}
          />
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium">{chosen?.label}</p>
              <p className="mt-0.5 text-xs text-text-muted">{chosen?.hint}</p>
            </div>
            {way === "project" && (
              <ProjectChoice breach={breach} draft={draft} onChange={setDraft} onUpload={() => setWay("upload")} />
            )}
            {way === "processor" && (
              <ProcessorPicker
                label="Vendor"
                value={draft.processor_uuid}
                onChange={(v) => setDraft({ ...draft, processor_uuid: v })}
              />
            )}
            {way === "data_source" && (
              <SourcePicker value={draft.source_uuid} onChange={(v) => setDraft({ ...draft, source_uuid: v })} />
            )}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setWay(null)}>
                Back
              </Button>
              <Button variant="primary" disabled={!ready(way, draft)} loading={look.isPending} onClick={() => find(way)}>
                <Search className="size-4" />
                Find the people
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function AffectedCard({ breach }: { breach: Breach }) {
  const toast = useToast();
  const query = useQuery<BreachAffected>({
    queryKey: keys.breach.affected(breach.breach_uuid),
    queryFn: () => listAffected(breach.breach_uuid),
  });
  // A list can bring in only people with no account, and those are no
  // revision: the count is both, as the notice below counts it.
  const contacts = useQuery({
    queryKey: keys.breach.contacts(breach.breach_uuid),
    queryFn: () => listBreachContacts(breach.breach_uuid),
  });
  const [adding, setAdding] = React.useState(false);
  const data = query.data;
  // Pages beyond the first belong to the listing they were read from; a fresh
  // listing (a new revision) starts from its own first page again.
  const [extra, setExtra] = React.useState<{
    from: BreachAffected | undefined;
    people: BreachAffected["people"];
    cursor: string | null;
  }>({ from: undefined, people: [], cursor: null });
  const [loadingMore, setLoadingMore] = React.useState(false);
  const paging = extra.from === data ? extra : { from: data, people: [], cursor: data?.next_cursor ?? null };
  const cursor = paging.cursor;

  async function loadMore() {
    if (!cursor) return;
    setLoadingMore(true);
    try {
      const page = await listAffected(breach.breach_uuid, cursor);
      setExtra({ from: data, people: [...paging.people, ...page.people], cursor: page.next_cursor });
    } catch (err) {
      toast.error("Could not load more", messageOf(err, "The server refused."));
    } finally {
      setLoadingMore(false);
    }
  }

  const people = [...(data?.people ?? []), ...paging.people];
  const listed = (data?.total ?? 0) + (contacts.data?.total ?? 0);
  const addedAt = (revision: number) => data?.revisions.find((r) => r.revision === revision)?.confirmed_at;
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Users className="mr-2 inline size-4" aria-hidden="true" />
          Affected people
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Rule 7(1): every affected Data Principal, to the best of current knowledge. Nobody listed is removed, and
          anyone added later is told when the notice is next sent.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className={listed > 0 ? "text-sm" : "text-sm text-text-muted"}>
            {query.isError ? (
              "The list could not be loaded."
            ) : query.isLoading || contacts.isLoading ? (
              "Loading…"
            ) : listed > 0 ? (
              <>
                <strong>{headcount(listed)}</strong> on the list.
              </>
            ) : (
              "Nobody is listed yet."
            )}
          </p>
          {breach.status === "open" && data && (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <UserPlus className="size-4" />
              Add people
            </Button>
          )}
        </div>
        {people.length > 0 && (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Person</Th>
                  <Th>How found</Th>
                  <Th>Reachable by</Th>
                  <Th>Added</Th>
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
                    <Td className="text-sm whitespace-nowrap">{formatDate(addedAt(p.revision))}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
            {cursor && (
              <Button variant="ghost" size="sm" loading={loadingMore} onClick={loadMore}>
                Show more
              </Button>
            )}
          </>
        )}
        <BreachContacts breach={breach} />
        {data && data.revisions.length > 0 && (
          <div>
            <p className="text-xs font-medium text-text-muted">How the list was built</p>
            <ol className="mt-1 space-y-1 text-xs text-text-muted">
              {data.revisions.map((r) => (
                <li key={r.revision_uuid}>
                  {formatDateTime(r.confirmed_at)} by {r.confirmed_by_name ?? "unknown"}: {history(r)}
                  {r.note && <span className="block whitespace-pre-wrap text-text">{r.note}</span>}
                </li>
              ))}
            </ol>
          </div>
        )}
        {adding && <AddPeople breach={breach} onClose={() => setAdding(false)} />}
      </CardBody>
    </Card>
  );
}
