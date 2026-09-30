/**
 * The cards on one breach: its duties and their clocks, the determination, the
 * assessment, and closing or reopening it.
 *
 * Every control renders the server's answer. Which duties exist, when each is
 * due and whether the breach may close all come back on the breach itself; a
 * refused action shows the server's sentence.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CalendarPlus, CheckCircle2, Lock, Plus, RotateCcw, Trash2 } from "lucide-react";
import * as React from "react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Field,
  Input,
  Mono,
  Select,
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  assessBreach,
  completeDuty,
  determineBreach,
  extendReport,
  markCertIn,
  transitionBreach,
} from "@/features/breach/api";
import { DutyStateBadge, OUTCOME_COPY, clockText } from "@/features/breach/components/copy";
import { instant, messageOf } from "@/features/breach/components/record-breach";
import { cn, formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type {
  Breach,
  BreachAssessmentFacts,
  BreachCategory,
  BreachDuty,
  BreachOutcome,
} from "@/types";

/** One write against a breach: the server answers with the breach, which
 *  replaces the cached copy, and the register is told to refetch. */
function useBreachWrite<A>(breach: Breach, fn: (uuid: string, args: A) => Promise<Breach>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: A) => fn(breach.breach_uuid, args),
    onSuccess: (fresh) => {
      qc.setQueryData(keys.breach.detail(breach.breach_uuid), fresh);
      void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
      void qc.invalidateQueries({ queryKey: ["breaches"] });
    },
  });
}

/* ------------------------------------------------------------------ duties */

function CompleteDialog({
  breach,
  duty,
  onClose,
}: {
  breach: Breach;
  duty: BreachDuty;
  onClose: () => void;
}) {
  const toast = useToast();
  const [when, setWhen] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [note, setNote] = React.useState("");
  const write = useBreachWrite(breach, (uuid, a: { at: string }) =>
    completeDuty(uuid, duty.duty, { occurred_at: a.at, reference: reference.trim(), note: note.trim() || null }),
  );
  const at = instant(when);
  async function save() {
    if (!at) return;
    try {
      await write.mutateAsync({ at });
      toast.success(`${duty.label}: recorded`, "The submission and its reference are on the record.");
      onClose();
    } catch (err) {
      toast.error("Not recorded", messageOf(err, "The server refused."));
    }
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title={`Record the submission - ${duty.label}`}
        description="The platform never submits to a regulator. Record what was submitted through the regulator's own channel, when, and the reference it returned."
      >
        <div className="space-y-3">
          <Field label="Submitted at" hint="When it was made, not when you are recording it" required>
            {(p) => <Input {...p} type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />}
          </Field>
          <Field label="Reference returned" hint="Acknowledgement or filing number" required>
            {(p) => <Input {...p} value={reference} maxLength={200} onChange={(e) => setReference(e.target.value)} />}
          </Field>
          <Field label="Note" hint="Optional">
            {(p) => <Textarea {...p} value={note} onChange={(e) => setNote(e.target.value)} />}
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" disabled={!at || !reference.trim()} loading={write.isPending} onClick={save}>
              Record
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ExtensionDialog({ breach, onClose }: { breach: Breach; onClose: () => void }) {
  const toast = useToast();
  const [asked, setAsked] = React.useState("");
  const [until, setUntil] = React.useState("");
  const [reference, setReference] = React.useState("");
  const write = useBreachWrite(breach, (uuid, a: { requested_at: string; allowed_until: string }) =>
    extendReport(uuid, { ...a, reference: reference.trim() || null }),
  );
  const requestedAt = instant(asked);
  const allowedUntil = instant(until);
  async function save() {
    if (!requestedAt || !allowedUntil) return;
    try {
      await write.mutateAsync({ requested_at: requestedAt, allowed_until: allowedUntil });
      toast.success("Extension recorded", "The detailed report is now due on the date the Board allowed.");
      onClose();
    } catch (err) {
      toast.error("Not recorded", messageOf(err, "The server refused."));
    }
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        title="The Board allowed longer"
        description="Rule 7(2)(b): the detailed report is due within 72 hours of becoming aware, or such longer period as the Board may allow. The initial intimation's clock does not move."
      >
        <div className="space-y-3">
          <Field label="Asked for at" required>
            {(p) => <Input {...p} type="datetime-local" value={asked} onChange={(e) => setAsked(e.target.value)} />}
          </Field>
          <Field label="Allowed until" required>
            {(p) => <Input {...p} type="datetime-local" value={until} onChange={(e) => setUntil(e.target.value)} />}
          </Field>
          <Field label="The Board's reference" hint="Optional">
            {(p) => <Input {...p} value={reference} maxLength={200} onChange={(e) => setReference(e.target.value)} />}
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" disabled={!requestedAt || !allowedUntil} loading={write.isPending} onClick={save}>
              Record the extension
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function DutiesCard({ breach }: { breach: Breach }) {
  const toast = useToast();
  const [completing, setCompleting] = React.useState<BreachDuty | null>(null);
  const [extending, setExtending] = React.useState(false);
  const certIn = useBreachWrite(breach, (uuid, _: void) => markCertIn(uuid));
  const open = breach.status === "open";
  const hasCertIn = breach.obligations.some((d) => d.duty === "cert_in");

  async function mark() {
    try {
      await certIn.mutateAsync();
      toast.success("CERT-In duty created", "Due six hours from when it was first noticed.");
    } catch (err) {
      toast.error("Not marked", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Duties</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Each runs on its own clock, in parallel. CERT-In runs from when it was first noticed; every DPDP duty from when
          the organisation became aware.
          {breach.without_delay_target_hours === null
            ? " No internal target is set for “without delay”: the time elapsed is shown and nothing is flagged."
            : ` The internal target for “without delay” is ${breach.without_delay_target_hours} hours.`}
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {breach.obligations.length === 0 ? (
          <p className="text-sm text-text-muted">
            No duty yet. A determination that this is a personal data breach creates the Board and principals duties;
            marking a reportable cyber incident creates CERT-In.
          </p>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Duty</Th>
                <Th>State</Th>
                <Th>Due</Th>
                <Th>Clock</Th>
                <Th>
                  <span className="sr-only">Actions</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {breach.obligations.map((d) => (
                <Tr key={d.obligation_uuid} className={cn((d.clock.overdue || d.clock.past_target) && "bg-danger-subtle/40")}>
                  <Td>
                    <span className="font-medium">{d.label}</span>
                    <span className="block text-xs text-text-subtle">{d.basis}</span>
                  </Td>
                  <Td>
                    <DutyStateBadge duty={d} />
                    {d.state === "done" && (
                      <span className="block text-xs text-text-subtle">
                        {formatDateTime(d.completed_at)} · <Mono>{d.reference}</Mono>
                      </span>
                    )}
                  </Td>
                  <Td>
                    {d.due_at ? formatDateTime(d.due_at) : "Without delay"}
                    {d.extended_until && <span className="block text-xs text-text-subtle">extended by the Board</span>}
                  </Td>
                  <Td className="text-sm">{clockText(d.state, d.clock)}</Td>
                  <Td className="text-right">
                    {open && d.state === "outstanding" && d.duty !== "principals" && (
                      <Button variant="secondary" size="sm" onClick={() => setCompleting(d)}>
                        <CheckCircle2 className="size-4" />
                        Record submission
                      </Button>
                    )}
                    {open && d.state === "outstanding" && d.duty === "board_report" && (
                      <Button variant="ghost" size="sm" onClick={() => setExtending(true)}>
                        <CalendarPlus className="size-4" />
                        Extension
                      </Button>
                    )}
                    {open && d.state === "outstanding" && d.duty === "principals" && (
                      <span className="text-xs text-text-subtle">Completes when every notice is delivered</span>
                    )}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
        {open && !hasCertIn && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border p-3 text-sm">
            <span>
              Is this a reportable cyber incident under the CERT-In Directions? CERT-In stands on its own test, apart
              from the DPDP determination.
            </span>
            <Button variant="secondary" size="sm" loading={certIn.isPending} onClick={mark}>
              <AlertTriangle className="size-4" />
              Mark reportable to CERT-In
            </Button>
          </div>
        )}
      </CardBody>
      {completing && <CompleteDialog breach={breach} duty={completing} onClose={() => setCompleting(null)} />}
      {extending && <ExtensionDialog breach={breach} onClose={() => setExtending(false)} />}
    </Card>
  );
}

/* ------------------------------------------------------------ determination */

export function DeterminationCard({ breach }: { breach: Breach }) {
  const toast = useToast();
  const [outcome, setOutcome] = React.useState<BreachOutcome>("yes");
  const [reasoning, setReasoning] = React.useState("");
  const [aware, setAware] = React.useState("");
  const write = useBreachWrite(
    breach,
    (uuid, a: { outcome: BreachOutcome; reasoning: string; became_aware_at: string | null }) =>
      determineBreach(uuid, a),
  );
  const awareAt = instant(aware);
  const ready = reasoning.trim() !== "" && (outcome !== "yes" || awareAt !== null);

  async function save() {
    try {
      await write.mutateAsync({
        outcome,
        reasoning: reasoning.trim(),
        became_aware_at: outcome === "yes" ? awareAt : null,
      });
      setReasoning("");
      setAware("");
      toast.success("Determination recorded", OUTCOME_COPY[outcome]);
    } catch (err) {
      toast.error("Not recorded", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Determination - s.2(u)</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Whether the event is a personal data breach is a person&apos;s judgement, recorded with its reasoning. The
          platform never infers it - not from encryption, not from anything. A revision is a new row; the latest is
          current.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {breach.determinations.length > 0 ? (
          <ol className="space-y-2 text-sm">
            {[...breach.determinations].reverse().map((d, i) => (
              <li key={d.determination_uuid} className={cn("rounded-md border border-border p-3", i > 0 && "opacity-70")}>
                <span className="font-medium">{OUTCOME_COPY[d.outcome]}</span>
                {d.became_aware_at && (
                  <span className="text-text-muted"> · aware {formatDateTime(d.became_aware_at)}</span>
                )}
                <span className="block text-xs text-text-subtle">
                  {formatDateTime(d.determined_at)} · {d.determined_by_name}
                  {i > 0 && " · superseded"}
                </span>
                <p className="mt-1 whitespace-pre-wrap">{d.reasoning}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-text-muted">Not yet determined.</p>
        )}
        {breach.status === "open" && (
          <div className="space-y-3 border-t border-border pt-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Determination" required>
                {(p) => (
                  <Select {...p} value={outcome} onChange={(e) => setOutcome(e.target.value as BreachOutcome)}>
                    <option value="yes">{OUTCOME_COPY.yes}</option>
                    <option value="no">{OUTCOME_COPY.no}</option>
                    <option value="pending">{OUTCOME_COPY.pending}</option>
                  </Select>
                )}
              </Field>
              {outcome === "yes" && (
                <Field label="Became aware at" hint="Starts every DPDP clock" required>
                  {(p) => <Input {...p} type="datetime-local" value={aware} onChange={(e) => setAware(e.target.value)} />}
                </Field>
              )}
            </div>
            <Field label="Reasoning" required>
              {(p) => <Textarea {...p} value={reasoning} onChange={(e) => setReasoning(e.target.value)} />}
            </Field>
            <div className="flex justify-end">
              <Button variant="primary" disabled={!ready} loading={write.isPending} onClick={save}>
                Record the determination
              </Button>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

/* --------------------------------------------------------------- assessment */

const FACTS: Array<{ key: keyof BreachAssessmentFacts; label: string; basis: string; sealed?: boolean }> = [
  { key: "nature_extent", label: "Nature and extent", basis: "7(1)(a), 7(2)(a)" },
  { key: "likely_impact", label: "Likely impact", basis: "7(2)(a)" },
  { key: "consequences", label: "Consequences likely for the people affected", basis: "7(1)(b)" },
  { key: "circumstances", label: "Events, circumstances and reasons", basis: "7(2)(b)(ii)" },
  { key: "mitigation", label: "Mitigation implemented, under way or proposed", basis: "7(1)(c), 7(2)(b)(iii)" },
  { key: "protective_steps", label: "What people can do to protect themselves", basis: "7(1)(d)" },
  { key: "caused_by_findings", label: "Findings on who caused it", basis: "7(2)(b)(iv)", sealed: true },
  { key: "remedial_measures", label: "Remedial measures against recurrence", basis: "7(2)(b)(v)" },
  { key: "contact_point", label: "Who answers people's questions", basis: "7(1)(e)" },
];

function emptyFacts(from: BreachAssessmentFacts | null): Record<keyof BreachAssessmentFacts, string> {
  return Object.fromEntries(FACTS.map((f) => [f.key, from?.[f.key] ?? ""])) as Record<
    keyof BreachAssessmentFacts,
    string
  >;
}

function CategoriesEditor({
  value,
  onChange,
}: {
  value: BreachCategory[];
  onChange: (next: BreachCategory[]) => void;
}) {
  const set = (i: number, patch: Partial<BreachCategory>) =>
    onChange(value.map((c, j) => (j === i ? { ...c, ...patch, key_exposed: (patch.sealed ?? c.sealed) ? (patch.key_exposed ?? c.key_exposed) : false } : c)));
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">Data categories exposed</legend>
      <p className="text-xs text-text-muted">
        One row per category. Sealing covers personal fields, not relationships - who consented to what is in plaintext -
        so say for each whether its values were sealed and whether the key was exposed. This is recorded for the
        determination and the report; it never delays or removes a duty.
      </p>
      {value.map((c, i) => (
        <div key={i} className="grid items-end gap-2 sm:grid-cols-[minmax(0,1fr)_auto_auto_auto]">
          <Field label="Category">
            {(p) => <Input {...p} value={c.category} onChange={(e) => set(i, { category: e.target.value })} />}
          </Field>
          <label className="flex items-center gap-2 pb-2 text-sm">
            <input type="checkbox" checked={c.sealed} onChange={(e) => set(i, { sealed: e.target.checked })} />
            Sealed
          </label>
          <label className="flex items-center gap-2 pb-2 text-sm">
            <input
              type="checkbox"
              checked={c.key_exposed}
              disabled={!c.sealed}
              onChange={(e) => set(i, { key_exposed: e.target.checked })}
            />
            Key exposed
          </label>
          <Button variant="ghost" size="sm" aria-label="Remove category" onClick={() => onChange(value.filter((_, j) => j !== i))}>
            <Trash2 className="size-4" />
          </Button>
        </div>
      ))}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onChange([...value, { category: "", sealed: false, key_exposed: false }])}
      >
        <Plus className="size-4" />
        Add a category
      </Button>
    </fieldset>
  );
}

export function AssessmentCard({ breach }: { breach: Breach }) {
  const toast = useToast();
  const latest = breach.assessment;
  const [editing, setEditing] = React.useState(false);
  const [facts, setFacts] = React.useState(() => emptyFacts(latest));
  const [categories, setCategories] = React.useState<BreachCategory[]>(latest?.categories ?? []);
  const [began, setBegan] = React.useState("");
  const write = useBreachWrite(breach, (uuid, _: void) =>
    assessBreach(uuid, {
      ...Object.fromEntries(Object.entries(facts).map(([k, v]) => [k, v.trim() || null])),
      began_at: instant(began),
      categories: categories.filter((c) => c.category.trim() !== ""),
    }),
  );

  function start() {
    setFacts(emptyFacts(latest));
    setCategories(latest?.categories ?? []);
    setBegan("");
    setEditing(true);
  }

  async function save() {
    try {
      const fresh = await write.mutateAsync();
      toast.success(`Revision ${fresh.assessment?.revision ?? ""} recorded`, "The previous revision is kept as it was.");
      setEditing(false);
    } catch (err) {
      toast.error("Not recorded", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assessment</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          What is known, for the notices and the Board&apos;s report. Revised as knowledge grows: each revision is a new
          row and the latest is current.
          {latest && ` Revision ${latest.revision} of ${breach.assessment_revisions}, ${formatDateTime(latest.revised_at)} by ${latest.revised_by_name ?? "unknown"}.`}
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {!editing && latest && (
          <DescriptionList>
            {latest.began_at && <DescriptionItem term="Began">{formatDateTime(latest.began_at)}</DescriptionItem>}
            {FACTS.filter((f) => latest[f.key]).map((f) => (
              <DescriptionItem key={f.key} term={`${f.label} · ${f.basis}`}>
                <span className="whitespace-pre-wrap">{latest[f.key]}</span>
              </DescriptionItem>
            ))}
            {latest.categories.length > 0 && (
              <DescriptionItem term="Data categories">
                <ul className="space-y-1">
                  {latest.categories.map((c) => (
                    <li key={c.category}>
                      {c.category}
                      <span className="text-text-muted">
                        {" - "}
                        {c.sealed ? (c.key_exposed ? "sealed, key exposed" : "sealed, key safe") : "not sealed"}
                      </span>
                    </li>
                  ))}
                </ul>
              </DescriptionItem>
            )}
          </DescriptionList>
        )}
        {!editing && !latest && <p className="text-sm text-text-muted">Nothing assessed yet.</p>}
        {!editing && breach.status === "open" && (
          <Button variant="secondary" size="sm" onClick={start}>
            <RotateCcw className="size-4" />
            {latest ? "Revise the assessment" : "Start the assessment"}
          </Button>
        )}
        {editing && (
          <div className="space-y-3">
            <Field label="Began" hint="If now known. Leave empty to keep what is recorded">
              {(p) => <Input {...p} type="datetime-local" value={began} onChange={(e) => setBegan(e.target.value)} />}
            </Field>
            {FACTS.map((f) => (
              <Field key={f.key} label={`${f.label} · ${f.basis}`} hint={f.sealed ? "Sealed; it may name an employee" : undefined}>
                {(p) => (
                  <Textarea
                    {...p}
                    value={facts[f.key]}
                    onChange={(e) => setFacts({ ...facts, [f.key]: e.target.value })}
                  />
                )}
              </Field>
            ))}
            <CategoriesEditor value={categories} onChange={setCategories} />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setEditing(false)}>
                Cancel
              </Button>
              <Button variant="primary" loading={write.isPending} onClick={save}>
                Record this revision
              </Button>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

/* ------------------------------------------------------------ open, closed */

export function BreachTransitions({ breach }: { breach: Breach }) {
  const toast = useToast();
  const [reason, setReason] = React.useState("");
  const write = useBreachWrite(breach, (uuid, a: { to: "open" | "closed"; reason: string | null }) =>
    transitionBreach(uuid, a),
  );
  const [move] = breach.transitions;
  if (!move) return null;

  async function go() {
    try {
      await write.mutateAsync({ to: move.to, reason: reason.trim() || null });
      setReason("");
      toast.success(move.to === "closed" ? "Breach closed" : "Breach reopened");
    } catch (err) {
      toast.error("Not moved", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{move.to === "closed" ? "Close" : "Reopen"}</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        {!move.allowed && (
          <Alert tone="info" title="Not yet">
            <ul className="list-disc pl-5">
              {move.blockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </Alert>
        )}
        {move.reason_required && (
          <Field label="Why it is being reopened" required>
            {(p) => <Textarea {...p} value={reason} onChange={(e) => setReason(e.target.value)} />}
          </Field>
        )}
        <Button
          variant={move.to === "closed" ? "primary" : "secondary"}
          disabled={!move.allowed || (move.reason_required && !reason.trim())}
          loading={write.isPending}
          onClick={go}
        >
          {move.to === "closed" ? <Lock className="size-4" /> : <RotateCcw className="size-4" />}
          {move.to === "closed" ? "Close the breach" : "Reopen the breach"}
        </Button>
      </CardBody>
    </Card>
  );
}
