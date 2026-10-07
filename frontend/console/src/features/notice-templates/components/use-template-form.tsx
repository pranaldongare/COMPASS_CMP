/**
 * Using a notice template on a project, by its ID (0044).
 *
 * The Privacy Office wrote it ahead of the project and gave out its ID. The
 * ID is looked up first, so whoever is attaching it sees what they are about
 * to get - its name, who it addresses, its purposes and languages - before
 * anything is made. Attaching makes the project's own draft notice, a copy;
 * it is then approved and published like any notice.
 */
"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { FormError } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Field, Input, Mono } from "@/components/ui/primitives";
import { useNoticeFromTemplate } from "@/features/notice-templates/mutations";
import { useFindNoticeTemplate } from "@/features/notice-templates/queries";
import { AUDIENCES } from "@/features/notices/components/notice-form";
import { useToast } from "@/providers";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function UseTemplateForm({
  projectUuid,
  onDone,
}: {
  projectUuid: string;
  onDone: () => void;
}) {
  const toast = useToast();
  const router = useRouter();
  const [typed, setTyped] = React.useState("");
  const [asked, setAsked] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const found = useFindNoticeTemplate(asked);
  const use = useNoticeFromTemplate(projectUuid);
  const t = found.data;

  function lookUp(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setAsked(typed.trim().toUpperCase());
  }

  async function create() {
    if (!t) return;
    setError(null);
    try {
      const notice = await use.mutateAsync(t.template_code);
      toast.success(
        `${notice.notice_code} made from ${t.template_code}`,
        "A draft. Approve each language, then publish it.",
      );
      onDone();
      router.push(`/notices/${notice.notice_uuid}`);
    } catch (err) {
      setError(messageOf(err, "Could not use that template."));
    }
  }

  const notFound = found.error?.status === 404;

  return (
    <div className="space-y-4">
      <FormError message={error} />
      <form method="post" onSubmit={lookUp} noValidate className="flex flex-wrap items-end gap-2">
        <div className="min-w-48 flex-1">
          <Field
            label="Template ID"
            hint="The ID the Privacy Office gave you, like TPL-0007."
            required
          >
            {(p) => (
              <Input
                {...p}
                value={typed}
                autoComplete="off"
                placeholder="TPL-0007"
                className="font-mono uppercase"
                onChange={(e) => setTyped(e.target.value)}
              />
            )}
          </Field>
        </div>
        <Button
          type="submit"
          variant="secondary"
          size="sm"
          className="h-9.5"
          disabled={typed.trim().length < 3}
          loading={found.isFetching}
        >
          <Search className="size-4" />
          Look up
        </Button>
      </form>

      {notFound && (
        <Alert tone="warning">
          <p className="text-sm">
            There is no template {asked}. Check the ID with the Privacy Office.
          </p>
        </Alert>
      )}
      {found.error && !notFound && (
        <Alert tone="danger">{found.error.userMessage()}</Alert>
      )}

      {t && (
        <div className="rounded-md border border-border p-4">
          <p className="text-sm font-semibold">
            <Mono>{t.template_code}</Mono> · {t.title}
          </p>
          <p className="mt-1 text-xs text-text-muted">
            For {AUDIENCES.find((a) => a.value === t.applicable_to)?.label ?? "an audience not yet decided"}
            {" · "}
            {t.languages.length} language{t.languages.length === 1 ? "" : "s"}
            {t.languages.length > 0 && ` (${t.languages.map((l) => l.language_code).join(", ")})`}
          </p>
          {t.purposes.length > 0 ? (
            <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm">
              {t.purposes.map((p) => (
                <li key={p.purpose_uuid}>
                  {p.name}
                  <span className="text-xs text-text-muted">
                    {p.is_mandatory ? " · mandatory" : " · optional"}
                    {p.status !== "active" && ` · ${p.status}, to be activated by the DPO`}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-text-muted">It carries no purposes yet.</p>
          )}
          {t.status === "retired" && (
            <Alert tone="warning" className="mt-3">
              <p className="text-sm">
                The Privacy Office has retired this template. Ask them which one to use instead.
              </p>
            </Alert>
          )}
        </div>
      )}

      {t && t.status === "active" && (
        <p className="text-xs text-text-muted">
          This project gets its own draft notice: the wording, the purposes and every language
          are copied, under the project&apos;s own notice code. Nothing is approved yet, and a
          later change to the template does not reach it.
        </p>
      )}

      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button
          type="button"
          variant="primary"
          disabled={!t || t.status !== "active"}
          loading={use.isPending}
          onClick={create}
        >
          Make this project&apos;s notice from it
        </Button>
      </DialogFooter>
    </div>
  );
}
