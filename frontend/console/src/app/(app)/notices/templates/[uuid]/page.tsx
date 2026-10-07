/**
 * One notice template (0044), the DPO's.
 *
 * It leads with its ID, because handing that to a study's R&D User is what a
 * template is for. Then what a notice made from it will carry - its details,
 * its purposes, its text in each language - each edited in place, and last the
 * project notices already made from it. Those are copies: nothing here changes
 * them, and the page says so wherever an edit might look as if it would.
 */
"use client";

import { ArrowLeft, Copy, Pencil, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
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
  Field,
  Mono,
  Select,
  Skeleton,
  Textarea,
} from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useEnums } from "@/features/meta";
import { TemplateForm } from "@/features/notice-templates/components/template-form";
import { TemplateStatusBadge } from "@/features/notice-templates/components/templates-panel";
import {
  useAttachTemplatePurpose,
  useDetachTemplatePurpose,
  useRemoveTemplateLanguage,
  useSetNoticeTemplateStatus,
  useSetTemplateLanguage,
} from "@/features/notice-templates/mutations";
import { useNoticeTemplate } from "@/features/notice-templates/queries";
import { AUDIENCES } from "@/features/notices/components/notice-form";
import { usePurposes } from "@/features/registry";
import { copyText } from "@/lib/browser";
import { formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";
import type { LanguageCode, NoticeTemplateDetail, NoticeTemplateLanguage } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export default function NoticeTemplatePage() {
  const params = useParams<{ uuid: string }>();
  const template = useNoticeTemplate(params?.uuid);
  const [editing, setEditing] = React.useState(false);

  if (template.isLoading) return <Skeleton className="h-96" />;
  if (template.error) {
    return (
      <Alert tone="danger" title="Could not load this template">
        {template.error.userMessage()}
      </Alert>
    );
  }
  const t = template.data;
  if (!t) return null;

  return (
    <>
      <PageHeader
        eyebrow="Notice template"
        breadcrumb={
          <Link
            href="/notices?tab=templates"
            className="inline-flex items-center gap-1 hover:underline"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Notice templates
          </Link>
        }
        title={t.title}
        description="A notice written before any project exists. Never shown to anybody until a project uses it."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <TemplateStatusBadge status={t.status} />
            <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
              <Pencil className="size-4" />
              Edit details
            </Button>
            <RetireButton template={t} />
          </div>
        }
      />

      <div className="space-y-6">
        <GiveTheId template={t} />

        <div className="grid gap-6 lg:grid-cols-2">
          <Details template={t} />
          <Purposes template={t} />
        </div>

        <Languages template={t} />
        <UsedBy template={t} />
      </div>

      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent title="Edit the template" size="lg">
          <TemplateForm template={t} onDone={() => setEditing(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}

function GiveTheId({ template: t }: { template: NoticeTemplateDetail }) {
  const toast = useToast();
  return (
    <Card>
      <CardBody className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-2xs font-semibold tracking-wide text-text-subtle uppercase">
            Template ID
          </p>
          <p className="mt-1 font-mono text-2xl font-semibold tracking-wide">{t.template_code}</p>
          <p className="mt-1 max-w-2xl text-sm text-text-muted">
            {t.status === "active"
              ? "Give this to the study's R&D User. On their project they choose Use a notice template and enter it; the project gets its own draft notice from it, to approve and publish."
              : "Retired: it can no longer be used. Notices already made from it are unaffected. Bring it back to use it again."}
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={async () => {
            const ok = await copyText(t.template_code);
            if (ok) toast.success(`${t.template_code} copied`);
            else toast.error("Could not copy", "Select the ID and copy it by hand.");
          }}
        >
          <Copy className="size-4" />
          Copy ID
        </Button>
      </CardBody>
    </Card>
  );
}

function RetireButton({ template: t }: { template: NoticeTemplateDetail }) {
  const toast = useToast();
  const status = useSetNoticeTemplateStatus(t.template_uuid);
  const retiring = t.status === "active";
  return (
    <Button
      variant={retiring ? "subtle" : "secondary"}
      size="sm"
      loading={status.isPending}
      onClick={async () => {
        try {
          await status.mutateAsync(retiring ? "retired" : "active");
          toast.success(
            retiring ? `${t.template_code} retired` : `${t.template_code} is back in use`,
            retiring ? "It can no longer be attached to a project." : undefined,
          );
        } catch (err) {
          toast.error("Not done", messageOf(err, "The server refused."));
        }
      }}
    >
      {retiring ? "Retire" : "Bring back"}
    </Button>
  );
}

function Details({ template: t }: { template: NoticeTemplateDetail }) {
  const audience = AUDIENCES.find((a) => a.value === t.applicable_to)?.label;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Details</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Written by {t.created_by_name} on {formatDateTime(t.created_at)} · last changed{" "}
          {formatDateTime(t.updated_at)}
        </p>
      </CardHeader>
      <CardBody>
        <DescriptionList>
          <DescriptionItem term="Applies to">{audience ?? "Not decided yet"}</DescriptionItem>
          <DescriptionItem term="DPO contact">{t.dpo_contact}</DescriptionItem>
          <DescriptionItem term="Withdraw consent">
            <span className="break-all">{t.withdraw_url}</span>
          </DescriptionItem>
          <DescriptionItem term="Exercise rights">
            <span className="break-all">{t.exercise_rights_url}</span>
          </DescriptionItem>
          <DescriptionItem term="Board complaint">
            <span className="break-all">{t.board_complaint_url}</span>
          </DescriptionItem>
          {t.note && <DescriptionItem term="Note for the collector">{t.note}</DescriptionItem>}
        </DescriptionList>
      </CardBody>
    </Card>
  );
}

function Purposes({ template: t }: { template: NoticeTemplateDetail }) {
  const toast = useToast();
  const attach = useAttachTemplatePurpose(t.template_uuid);
  const detach = useDetachTemplatePurpose(t.template_uuid);
  const purposes = usePurposes({ limit: 200, sort: "name" });
  const [chosen, setChosen] = React.useState("");
  const [mandatory, setMandatory] = React.useState(false);
  const attached = new Set(t.purposes.map((p) => p.purpose_uuid));
  const options = (purposes.data?.items ?? []).filter(
    (p) => p.status !== "retired" && !attached.has(p.purpose_uuid),
  );

  async function add() {
    try {
      await attach.mutateAsync({ purpose_uuid: chosen, is_mandatory: mandatory });
      setChosen("");
      setMandatory(false);
    } catch (err) {
      toast.error("Not added", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Purposes · {t.purposes.length}</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          From the purpose register. A draft purpose can be put here; a notice made from the
          template cannot be published until the purpose is activated.
        </p>
      </CardHeader>
      <CardBody className="space-y-3">
        {t.purposes.length === 0 ? (
          <p className="text-sm text-text-muted">No purposes yet.</p>
        ) : (
          <ul className="divide-y divide-border rounded-md border border-border">
            {t.purposes.map((p) => (
              <li key={p.purpose_uuid} className="flex flex-wrap items-center gap-2 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    {p.name} <Mono className="text-xs text-text-subtle">{p.purpose_code}</Mono>
                  </p>
                  <p className="text-xs text-text-muted">
                    {p.is_mandatory ? "Mandatory" : "Optional"}
                    {p.data_categories.length > 0 && ` · ${p.data_categories.join(", ")}`}
                  </p>
                </div>
                {p.status !== "active" && <Badge tone="warning">{p.status}</Badge>}
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Remove ${p.name}`}
                  loading={detach.isPending && detach.variables === p.purpose_uuid}
                  onClick={() =>
                    detach
                      .mutateAsync(p.purpose_uuid)
                      .catch((err) => toast.error("Not removed", messageOf(err, "Refused.")))
                  }
                >
                  <Trash2 className="size-4" />
                </Button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-56 flex-1">
            <Field label="Add a purpose">
              {(p) => (
                <Select
                  {...p}
                  value={chosen}
                  disabled={purposes.isLoading}
                  onChange={(e) => setChosen(e.target.value)}
                >
                  <option value="">Choose a purpose…</option>
                  {options.map((o) => (
                    <option key={o.purpose_uuid} value={o.purpose_uuid}>
                      {o.name} ({o.purpose_code}){o.status === "draft" ? " - draft" : ""}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>
          <label className="flex h-9.5 items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="size-4 rounded border-border-strong accent-[var(--accent)]"
              checked={mandatory}
              onChange={(e) => setMandatory(e.target.checked)}
            />
            Mandatory
          </label>
          <Button
            variant="secondary"
            size="sm"
            className="h-9.5"
            disabled={!chosen}
            loading={attach.isPending}
            onClick={add}
          >
            <Plus className="size-4" />
            Add
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}

function Languages({ template: t }: { template: NoticeTemplateDetail }) {
  const toast = useToast();
  const { data: enums } = useEnums();
  const remove = useRemoveTemplateLanguage(t.template_uuid);
  const [editing, setEditing] = React.useState<NoticeTemplateLanguage | "new" | null>(null);
  const labels = new Map((enums?.language_code ?? []).map((o) => [o.value, o.label]));
  const missing = (enums?.language_code ?? []).filter(
    (o) => !t.languages.some((l) => l.language_code === o.value),
  );

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>Text · {t.languages.length} language{t.languages.length === 1 ? "" : "s"}</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            What a data principal will read once a project uses it. Each language is approved
            on the project&apos;s notice, not here.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          disabled={enums !== undefined && missing.length === 0}
          onClick={() => setEditing("new")}
        >
          <Plus className="size-4" />
          Add a language
        </Button>
      </CardHeader>
      <CardBody className="space-y-3">
        {t.languages.length === 0 ? (
          <p className="text-sm text-text-muted">No text yet. Add English first.</p>
        ) : (
          t.languages.map((l) => (
            <div key={l.language_code} className="rounded-md border border-border">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2">
                <p className="text-sm font-medium">
                  {labels.get(l.language_code) ?? l.language_code}
                  <span className="ml-2 text-xs font-normal text-text-muted">
                    {l.updated_by_name} · {formatDateTime(l.updated_at)}
                  </span>
                </p>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => setEditing(l)}>
                    <Pencil className="size-4" />
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Remove ${labels.get(l.language_code) ?? l.language_code}`}
                    loading={remove.isPending && remove.variables === l.language_code}
                    onClick={() =>
                      remove
                        .mutateAsync(l.language_code)
                        .catch((err) => toast.error("Not removed", messageOf(err, "Refused.")))
                    }
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </div>
              <p className="max-h-40 overflow-y-auto px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap text-text-muted">
                {l.rendered_text}
              </p>
            </div>
          ))
        )}
      </CardBody>

      <Dialog open={editing !== null} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent
          title={editing === "new" ? "Add a language" : "Edit the text"}
          size="lg"
        >
          {editing !== null && (
            <LanguageEditor
              template={t}
              existing={editing === "new" ? undefined : editing}
              choices={editing === "new" ? missing : []}
              onDone={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function LanguageEditor({
  template: t,
  existing,
  choices,
  onDone,
}: {
  template: NoticeTemplateDetail;
  existing?: NoticeTemplateLanguage;
  choices: { value: string; label: string }[];
  onDone: () => void;
}) {
  const toast = useToast();
  const save = useSetTemplateLanguage(t.template_uuid);
  const [code, setCode] = React.useState<string>(
    existing?.language_code ?? choices[0]?.value ?? "english",
  );
  const [text, setText] = React.useState(existing?.rendered_text ?? "");
  const [error, setError] = React.useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await save.mutateAsync({ language_code: code as LanguageCode, rendered_text: text });
      toast.success("Text saved");
      onDone();
    } catch (err) {
      setError(messageOf(err, "The server refused."));
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className="space-y-4">
      {error && <Alert tone="danger">{error}</Alert>}
      {!existing && (
        <Field label="Language" required>
          {(p) => (
            <Select {...p} value={code} onChange={(e) => setCode(e.target.value)}>
              {choices.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
      )}
      <Field
        label="Notice text"
        hint="Notices already made from this template keep their own text."
        required
      >
        {(p) => (
          <Textarea
            {...p}
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={16}
            className="font-mono text-xs leading-relaxed"
          />
        )}
      </Field>
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={!text.trim()} loading={save.isPending}>
          Save text
        </Button>
      </DialogFooter>
    </form>
  );
}

function UsedBy({ template: t }: { template: NoticeTemplateDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Used by · {t.notices.length}</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Project notices made from this template. Each is the project&apos;s own copy, approved
          and published there.
        </p>
      </CardHeader>
      <CardBody>
        {t.notices.length === 0 ? (
          <p className="text-sm text-text-muted">No project has used it yet.</p>
        ) : (
          <ul className="divide-y divide-border rounded-md border border-border">
            {t.notices.map((n) => (
              <li key={n.notice_uuid} className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm">
                <Link
                  href={`/notices/${n.notice_uuid}`}
                  className="font-medium text-accent-text hover:underline"
                >
                  {n.notice_code} v{n.version}
                </Link>
                <Link
                  href={`/projects/${n.project_uuid}`}
                  className="text-text-muted hover:text-text hover:underline"
                >
                  {n.project_name}
                </Link>
                <StatusBadge kind="notice" value={n.status} />
                <span className="ml-auto text-xs text-text-muted">
                  {formatDateTime(n.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
