/**
 * A Legal office template's versions (0053, ADR 0033), on its page.
 *
 * A version is the legal text Legal approves once for every activity made
 * from it: the locked text with its two slots, the purposes an activity may
 * choose and which it must carry, the description slot's guidance and limit,
 * and whether moving to it asks participants to consent again. A draft is
 * edited here; Approve checks it, hashes each language and freezes it. A
 * later change is the next version, which opens as a copy.
 */
"use client";

import { ArrowDown, ArrowUp, CheckCircle2, Eye, Plus, Trash2, XCircle } from "lucide-react";
import * as React from "react";

import { ConfirmDialog } from "@/components/ui/dialog";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  EmptyState,
  Field,
  Input,
  Mono,
  Select,
  Skeleton,
  Table,
  Td,
  Textarea,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { useEnums } from "@/features/meta";
import {
  useApproveTemplateVersion,
  useOpenTemplateVersion,
  useRemoveVersionLanguage,
  useRetireTemplateVersion,
  useSetVersionLanguage,
  useSetVersionPurposes,
  useUpdateTemplateVersion,
} from "@/features/notice-templates/mutations";
import {
  useTemplateVersion,
  useTemplateVersions,
  useVersionPreview,
} from "@/features/notice-templates/queries";
import { AUDIENCES } from "@/features/notices/components/notice-form";
import { usePurposes } from "@/features/registry";
import { formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type {
  LanguageCode,
  NoticeAudience,
  NoticeTemplateDetail,
  TemplateVersion,
  TemplateVersionDetail,
} from "@/types";

const SLOTS = ["{{purposes}}", "{{description}}"] as const;

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function VersionStatusBadge({ status }: { status: TemplateVersion["status"] }) {
  if (status === "approved")
    return (
      <Badge tone="success" dot>
        Approved
      </Badge>
    );
  if (status === "retired")
    return (
      <Badge tone="neutral" dot>
        Retired
      </Badge>
    );
  return (
    <Badge tone="warning" dot>
      Draft
    </Badge>
  );
}

export function VersionsPanel({
  template,
  canWrite,
}: {
  template: NoticeTemplateDetail;
  canWrite: boolean;
}) {
  const toast = useToast();
  const versions = useTemplateVersions(template.template_uuid);
  const open = useOpenTemplateVersion(template.template_uuid);
  const rows = versions.data ?? [];
  const [chosen, setChosen] = React.useState<number | null>(null);
  const shown = chosen ?? rows[0]?.version ?? null;
  const hasDraft = rows.some((v) => v.status === "draft");

  async function openNext() {
    try {
      const made = await open.mutateAsync();
      setChosen(made.version);
      toast.success(
        `Version ${made.version} opened`,
        made.version > 1 ? "It starts as a copy of the last version." : undefined,
      );
    } catch (err) {
      toast.error("Not opened", messageOf(err, "The server refused."));
    }
  }

  const openButton =
    canWrite && !hasDraft && template.status === "active" ? (
      <Button variant="primary" size="sm" loading={open.isPending} onClick={openNext}>
        <Plus className="size-4" />
        Open version {(rows[0]?.version ?? 0) + 1}
      </Button>
    ) : null;

  if (versions.isLoading) return <Skeleton className="h-40" />;
  if (versions.error)
    return (
      <Alert tone="danger" title="Could not load the versions">
        {versions.error.userMessage()}
      </Alert>
    );

  return (
    <div className="space-y-5">
      <p className="max-w-3xl text-sm text-text-muted">
        A version is the legal text you approve once. Every activity made from it inherits that
        approval and is composed from it: the chosen purposes fill {"{{purposes}}"} and the HR
        PoC&apos;s description fills {"{{description}}"}. An approved version never changes; a
        change is the next version.
      </p>
      {rows.length === 0 ? (
        <EmptyState
          title="No version yet"
          description="Open version 1 to write the text and choose its purposes."
          action={openButton}
        />
      ) : (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-3">
            <CardTitle>Versions</CardTitle>
            {openButton}
          </CardHeader>
          <CardBody>
            <Table>
              <caption className="sr-only">Versions of {template.template_code}</caption>
              <thead>
                <tr>
                  <Th>Version</Th>
                  <Th>Status</Th>
                  <Th>Purposes</Th>
                  <Th>Languages</Th>
                  <Th>Activities</Th>
                  <Th>Approved</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((v) => (
                  <Tr key={v.version_uuid} className={v.version === shown ? "bg-accent-subtle" : ""}>
                    <Td>
                      <button
                        type="button"
                        className="font-medium text-accent-text hover:underline"
                        onClick={() => setChosen(v.version)}
                      >
                        v{v.version}
                      </button>
                      {v.reconsent_required && (
                        <span className="ml-2 text-2xs text-text-muted">re-consent</span>
                      )}
                    </Td>
                    <Td>
                      <VersionStatusBadge status={v.status} />
                    </Td>
                    <Td className="tabular text-text-muted">{v.purpose_count}</Td>
                    <Td className="tabular text-text-muted">{v.language_count}</Td>
                    <Td className="tabular text-text-muted">{v.activity_count}</Td>
                    <Td className="whitespace-nowrap text-text-muted">
                      {v.approved_at ? formatDateTime(v.approved_at) : "—"}
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </CardBody>
        </Card>
      )}
      {shown !== null && (
        <VersionView templateUuid={template.template_uuid} n={shown} canWrite={canWrite} />
      )}
    </div>
  );
}

function VersionView({
  templateUuid,
  n,
  canWrite,
}: {
  templateUuid: string;
  n: number;
  canWrite: boolean;
}) {
  const version = useTemplateVersion(templateUuid, n);
  if (version.isLoading) return <Skeleton className="h-64" />;
  if (version.error)
    return <Alert tone="danger">{version.error.userMessage()}</Alert>;
  const v = version.data;
  if (!v) return null;
  const editable = canWrite && v.status === "draft";
  return (
    <div className="space-y-5" id="version">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Version {v.version}</h2>
          <VersionStatusBadge status={v.status} />
          {v.approved_at && (
            <span className="text-xs text-text-muted">
              approved by {v.approved_by_name} on {formatDateTime(v.approved_at)}
            </span>
          )}
        </div>
        {canWrite && <VersionActions templateUuid={templateUuid} version={v} />}
      </div>
      <div className="grid gap-5 lg:grid-cols-2 lg:items-start">
        <VersionFields templateUuid={templateUuid} version={v} editable={editable} />
        <VersionPurposes templateUuid={templateUuid} version={v} editable={editable} />
      </div>
      <VersionText templateUuid={templateUuid} version={v} editable={editable} />
      <VersionPreview templateUuid={templateUuid} version={v} />
    </div>
  );
}

function VersionActions({
  templateUuid,
  version: v,
}: {
  templateUuid: string;
  version: TemplateVersionDetail;
}) {
  const toast = useToast();
  const approve = useApproveTemplateVersion(templateUuid, v.version);
  const retire = useRetireTemplateVersion(templateUuid, v.version);
  const [asking, setAsking] = React.useState<"approve" | "retire" | null>(null);

  async function act() {
    try {
      if (asking === "approve") {
        await approve.mutateAsync();
        toast.success(`Version ${v.version} approved`, "It is frozen; activities can use it.");
      } else {
        await retire.mutateAsync();
        toast.success(`Version ${v.version} retired`, "Activities already on it continue.");
      }
      setAsking(null);
    } catch (err) {
      toast.error("Not done", messageOf(err, "The server refused."));
      setAsking(null);
    }
  }

  return (
    <>
      {v.status === "draft" && (
        <Button variant="primary" size="sm" onClick={() => setAsking("approve")}>
          <CheckCircle2 className="size-4" />
          Approve
        </Button>
      )}
      {v.status === "approved" && (
        <Button variant="subtle" size="sm" onClick={() => setAsking("retire")}>
          Retire
        </Button>
      )}
      <ConfirmDialog
        open={asking !== null}
        onOpenChange={(o) => !o && setAsking(null)}
        title={asking === "approve" ? `Approve version ${v.version}?` : `Retire version ${v.version}?`}
        consequence={
          asking === "approve"
            ? "Its text, purposes and fields are frozen and hashed. Every activity made from it inherits this approval. A later change is the next version."
            : "No new activity can start on it. Activities already on it continue with it."
        }
        confirmLabel={asking === "approve" ? "Approve" : "Retire"}
        tone={asking === "approve" ? "primary" : "danger"}
        loading={approve.isPending || retire.isPending}
        onConfirm={act}
      />
    </>
  );
}

function VersionFields({
  templateUuid,
  version: v,
  editable,
}: {
  templateUuid: string;
  version: TemplateVersionDetail;
  editable: boolean;
}) {
  const toast = useToast();
  const update = useUpdateTemplateVersion(templateUuid, v.version);
  const [draft, setDraft] = React.useState(() => ({
    slot_guidance: v.slot_guidance ?? "",
    slot_max_length: String(v.slot_max_length),
    reconsent_required: v.reconsent_required,
    applicable_to: v.applicable_to ?? "",
    dpo_contact: v.dpo_contact,
    withdraw_url: v.withdraw_url,
    exercise_rights_url: v.exercise_rights_url,
    board_complaint_url: v.board_complaint_url,
  }));
  const audience = AUDIENCES.find((a) => a.value === v.applicable_to)?.label;

  if (!editable) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>The version</CardTitle>
        </CardHeader>
        <CardBody>
          <DescriptionList>
            <DescriptionItem term="Description slot">
              up to {v.slot_max_length} characters
              {v.slot_guidance && (
                <span className="block text-text-muted">{v.slot_guidance}</span>
              )}
            </DescriptionItem>
            <DescriptionItem term="Re-consent">
              {v.reconsent_required
                ? "Moving an activity to it asks participants again"
                : "Not needed"}
            </DescriptionItem>
            <DescriptionItem term="Applies to">{audience ?? "Not decided yet"}</DescriptionItem>
            <DescriptionItem term="Contact">{v.dpo_contact}</DescriptionItem>
            <DescriptionItem term="Withdraw consent">
              <span className="break-all">{v.withdraw_url}</span>
            </DescriptionItem>
            <DescriptionItem term="Exercise rights">
              <span className="break-all">{v.exercise_rights_url}</span>
            </DescriptionItem>
            <DescriptionItem term="Board complaint">
              <span className="break-all">{v.board_complaint_url}</span>
            </DescriptionItem>
          </DescriptionList>
        </CardBody>
      </Card>
    );
  }

  async function save() {
    try {
      await update.mutateAsync({
        slot_guidance: draft.slot_guidance,
        slot_max_length: Number(draft.slot_max_length),
        reconsent_required: draft.reconsent_required,
        applicable_to: (draft.applicable_to || null) as NoticeAudience | null,
        dpo_contact: draft.dpo_contact,
        withdraw_url: draft.withdraw_url,
        exercise_rights_url: draft.exercise_rights_url,
        board_complaint_url: draft.board_complaint_url,
      });
      toast.success("Saved");
    } catch (err) {
      toast.error("Not saved", messageOf(err, "The server refused."));
    }
  }

  const set = (key: keyof typeof draft) => (value: string | boolean) =>
    setDraft((d) => ({ ...d, [key]: value }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>The version</CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        <Field
          label="Guidance for the description"
          hint="Shown to the HR PoC beside the description box: what to say, and what not to."
        >
          {(p) => (
            <Textarea
              {...p}
              rows={2}
              value={draft.slot_guidance}
              onChange={(e) => set("slot_guidance")(e.target.value)}
            />
          )}
        </Field>
        <Field label="Longest description" hint="100 to 4,000 characters.">
          {(p) => (
            <Input
              {...p}
              type="number"
              min={100}
              max={4000}
              value={draft.slot_max_length}
              onChange={(e) => set("slot_max_length")(e.target.value)}
            />
          )}
        </Field>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={draft.reconsent_required}
            onChange={(e) => set("reconsent_required")(e.target.checked)}
            className="mt-0.5 size-4 rounded border-border-strong accent-[var(--accent)]"
          />
          <span>
            A material change: moving an activity to this version asks its participants to
            consent again
          </span>
        </label>
        <Field label="Applies to" hint="Required before the version can be approved.">
          {(p) => (
            <Select
              {...p}
              value={draft.applicable_to}
              onChange={(e) => set("applicable_to")(e.target.value)}
            >
              <option value="">Not decided yet</option>
              {AUDIENCES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Contact" hint="The Legal office's address, shown on every notice.">
          {(p) => (
            <Input {...p} value={draft.dpo_contact} onChange={(e) => set("dpo_contact")(e.target.value)} />
          )}
        </Field>
        <Field label="Withdraw consent URL">
          {(p) => (
            <Input {...p} value={draft.withdraw_url} onChange={(e) => set("withdraw_url")(e.target.value)} />
          )}
        </Field>
        <Field label="Exercise rights URL">
          {(p) => (
            <Input
              {...p}
              value={draft.exercise_rights_url}
              onChange={(e) => set("exercise_rights_url")(e.target.value)}
            />
          )}
        </Field>
        <Field label="Board complaint URL">
          {(p) => (
            <Input
              {...p}
              value={draft.board_complaint_url}
              onChange={(e) => set("board_complaint_url")(e.target.value)}
            />
          )}
        </Field>
        <div className="flex justify-end">
          <Button variant="secondary" size="sm" loading={update.isPending} onClick={save}>
            Save
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}

function VersionPurposes({
  templateUuid,
  version: v,
  editable,
}: {
  templateUuid: string;
  version: TemplateVersionDetail;
  editable: boolean;
}) {
  const toast = useToast();
  const save = useSetVersionPurposes(templateUuid, v.version);
  const catalogue = usePurposes({ limit: 200, sort: "name" });
  const [list, setList] = React.useState(() =>
    v.purposes.map((p) => ({
      purpose_uuid: p.purpose_uuid,
      name: p.name,
      status: p.status,
      is_mandatory: p.is_mandatory,
    })),
  );
  const [adding, setAdding] = React.useState("");
  const chosen = new Set(list.map((p) => p.purpose_uuid));
  const offered = (catalogue.data?.items ?? []).filter(
    (p) => p.status !== "retired" && !chosen.has(p.purpose_uuid),
  );

  function move(i: number, by: number) {
    setList((l) => {
      const next = [...l];
      const [item] = next.splice(i, 1);
      next.splice(i + by, 0, item);
      return next;
    });
  }

  async function submit() {
    try {
      await save.mutateAsync(
        list.map((p) => ({ purpose_uuid: p.purpose_uuid, is_mandatory: p.is_mandatory })),
      );
      toast.success("Purposes saved");
    } catch (err) {
      toast.error("Not saved", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Purposes an activity may choose</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          A mandatory purpose is always on the activity&apos;s notice; the others the HR PoC
          chooses. Every one must be active before the version is approved.
        </p>
      </CardHeader>
      <CardBody>
        {list.length === 0 && <p className="text-sm text-text-muted">None yet.</p>}
        <ul className="divide-y divide-border">
          {list.map((p, i) => (
            <li key={p.purpose_uuid} className="flex flex-wrap items-center gap-2 py-2 text-sm">
              <span className="min-w-0 flex-1">
                {p.name}
                {p.status !== "active" && (
                  <span className="text-xs text-warning-text"> · {p.status}</span>
                )}
              </span>
              {editable ? (
                <>
                  <label className="flex items-center gap-1 text-xs">
                    <input
                      type="checkbox"
                      checked={p.is_mandatory}
                      onChange={(e) =>
                        setList((l) =>
                          l.map((x, j) => (j === i ? { ...x, is_mandatory: e.target.checked } : x)),
                        )
                      }
                      className="size-4 rounded border-border-strong accent-[var(--accent)]"
                    />
                    Mandatory
                  </label>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label="Move up"
                    disabled={i === 0}
                    onClick={() => move(i, -1)}
                  >
                    <ArrowUp className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label="Move down"
                    disabled={i === list.length - 1}
                    onClick={() => move(i, 1)}
                  >
                    <ArrowDown className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Remove ${p.name}`}
                    onClick={() => setList((l) => l.filter((_, j) => j !== i))}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </>
              ) : (
                <span className="text-xs text-text-muted">
                  {p.is_mandatory ? "mandatory" : "optional"}
                </span>
              )}
            </li>
          ))}
        </ul>
        {editable && (
          <div className="mt-3 space-y-3">
            <div className="flex gap-2">
              <Select
                aria-label="Add a purpose"
                value={adding}
                onChange={(e) => setAdding(e.target.value)}
              >
                <option value="">Add a purpose…</option>
                {offered.map((p) => (
                  <option key={p.purpose_uuid} value={p.purpose_uuid}>
                    {p.name} ({p.purpose_code}){p.status === "draft" ? " · draft" : ""}
                  </option>
                ))}
              </Select>
              <Button
                variant="secondary"
                size="sm"
                disabled={!adding}
                onClick={() => {
                  const p = offered.find((x) => x.purpose_uuid === adding);
                  if (!p) return;
                  setList((l) => [
                    ...l,
                    { purpose_uuid: p.purpose_uuid, name: p.name, status: p.status, is_mandatory: false },
                  ]);
                  setAdding("");
                }}
              >
                <Plus className="size-4" />
                Add
              </Button>
            </div>
            <div className="flex justify-end">
              <Button variant="secondary" size="sm" loading={save.isPending} onClick={submit}>
                Save purposes
              </Button>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function SlotCheck({ text }: { text: string }) {
  return (
    <span className="flex flex-wrap gap-3 text-xs">
      {SLOTS.map((slot) => {
        const n = text.split(slot).length - 1;
        const ok = n === 1;
        return (
          <span key={slot} className={ok ? "text-success-text" : "text-warning-text"}>
            {ok ? (
              <CheckCircle2 className="mr-1 inline size-3.5" aria-hidden="true" />
            ) : (
              <XCircle className="mr-1 inline size-3.5" aria-hidden="true" />
            )}
            <Mono>{slot}</Mono> {n === 1 ? "once" : n === 0 ? "missing" : `${n} times`}
          </span>
        );
      })}
    </span>
  );
}

function VersionText({
  templateUuid,
  version: v,
  editable,
}: {
  templateUuid: string;
  version: TemplateVersionDetail;
  editable: boolean;
}) {
  const toast = useToast();
  const { data: enums } = useEnums();
  const setText = useSetVersionLanguage(templateUuid, v.version);
  const remove = useRemoveVersionLanguage(templateUuid, v.version);
  const [language, setLanguage] = React.useState<LanguageCode>(
    (v.languages[0]?.language_code ?? "english") as LanguageCode,
  );
  const current = v.languages.find((l) => l.language_code === language);
  const [text, setTextValue] = React.useState(current?.locked_text ?? "");
  const box = React.useRef<HTMLTextAreaElement | null>(null);

  function pick(code: LanguageCode) {
    setLanguage(code);
    setTextValue(v.languages.find((l) => l.language_code === code)?.locked_text ?? "");
  }

  function insert(slot: string) {
    const el = box.current;
    const at = el?.selectionStart ?? text.length;
    const end = el?.selectionEnd ?? at;
    setTextValue(text.slice(0, at) + slot + text.slice(end));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(at + slot.length, at + slot.length);
    });
  }

  async function save() {
    try {
      await setText.mutateAsync({ language_code: language, locked_text: text });
      toast.success("Text saved");
    } catch (err) {
      toast.error("Not saved", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Locked text</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          The legal text, exactly as served, with {"{{purposes}}"} and {"{{description}}"} once
          each. English is required.
        </p>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            aria-label="Language"
            value={language}
            onChange={(e) => pick(e.target.value as LanguageCode)}
          >
            {(enums?.language_code ?? [{ value: "english", label: "English" }])
              .filter((o) => editable || v.languages.some((l) => l.language_code === o.value))
              .map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                  {v.languages.some((l) => l.language_code === o.value) ? " ✓" : ""}
                </option>
              ))}
          </Select>
          {current?.content_hash && (
            <span className="text-xs text-text-muted">
              hash <Mono>{current.content_hash.slice(0, 16)}…</Mono>
            </span>
          )}
        </div>
        {editable ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              {SLOTS.map((slot) => (
                <Button key={slot} variant="secondary" size="sm" onClick={() => insert(slot)}>
                  Insert <Mono>{slot}</Mono>
                </Button>
              ))}
              <SlotCheck text={text} />
            </div>
            <Textarea
              ref={box}
              aria-label="Locked text"
              rows={14}
              value={text}
              onChange={(e) => setTextValue(e.target.value)}
              className="min-h-64 font-mono text-xs leading-relaxed"
            />
            <div className="flex justify-between gap-2">
              {current ? (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={remove.isPending}
                  onClick={async () => {
                    try {
                      await remove.mutateAsync(language);
                      toast.success("Language removed");
                    } catch (err) {
                      toast.error("Not removed", messageOf(err, "The server refused."));
                    }
                  }}
                >
                  <Trash2 className="size-4" />
                  Remove this language
                </Button>
              ) : (
                <span />
              )}
              <Button
                variant="secondary"
                size="sm"
                disabled={!text.trim()}
                loading={setText.isPending}
                onClick={save}
              >
                Save text
              </Button>
            </div>
          </>
        ) : (
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-bg-inset p-3 font-mono text-xs leading-relaxed">
            {current?.locked_text ?? "No text in this language."}
          </pre>
        )}
      </CardBody>
    </Card>
  );
}

function VersionPreview({
  templateUuid,
  version: v,
}: {
  templateUuid: string;
  version: TemplateVersionDetail;
}) {
  const [description, setDescription] = React.useState("");
  const [asked, setAsked] = React.useState<string | null>(null);
  const preview = useVersionPreview(templateUuid, v.version, asked);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Preview</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          What an activity made from this version would serve, with every purpose on its list
          and the description below (or a sample).
        </p>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-64 flex-1">
            <Field
              label="A description"
              hint={v.slot_guidance ?? `Up to ${v.slot_max_length} characters, no links.`}
            >
              {(p) => (
                <Input
                  {...p}
                  value={description}
                  maxLength={v.slot_max_length}
                  onChange={(e) => setDescription(e.target.value)}
                />
              )}
            </Field>
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="h-9.5"
            loading={preview.isFetching}
            onClick={() => setAsked(description)}
          >
            <Eye className="size-4" />
            Preview
          </Button>
        </div>
        {preview.error && <Alert tone="warning">{preview.error.userMessage()}</Alert>}
        {(preview.data ?? []).map((p) => (
          <div key={p.language_code} className="space-y-1">
            <p className="text-xs text-text-muted">
              {p.language_code} · hash <Mono>{p.content_hash.slice(0, 16)}…</Mono>
            </p>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-bg-inset p-3 text-sm leading-relaxed">
              {p.text}
            </pre>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}
