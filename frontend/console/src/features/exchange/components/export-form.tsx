/**
 * Generating a project's export.
 *
 * Two kinds since 2026-11-11, and the choice is the only one on the form. The
 * project export is one CSV per project that carries the context on every row,
 * so an agent at the collection point does not join two files by hand. The
 * consented list is the file the Data Collection Tool loads, to that tool's
 * fixed data contract: only the people whose consent is fully in force, and
 * only what an agent needs to recognise and tag them.
 *
 * What either contains still varies, but by *who is asking* rather than by
 * anything on this form. A collection owner gets the people who consented at the
 * sites they run; a DPO gets all of them. Offering that as a control would be
 * offering somebody a choice they do not have.
 *
 * The warning is not decoration. Both files carry personal data, and generating
 * either writes one disclosure row per person — the record that makes "who was
 * my data shared with?" answerable, and the reason generating and downloading
 * are separate.
 */
"use client";

import { AlertTriangle, Download } from "lucide-react";

import { FormError } from "@/components/forms";
import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button } from "@/components/ui/primitives";
import { useCreateExport, type ExportCreated, type ExportKind } from "@/features/exchange";
import { useToast } from "@/providers";
import * as React from "react";

const KINDS: { kind: ExportKind; label: string; hint: string }[] = [
  {
    kind: "project_export",
    label: "Project export",
    hint: "Every consent with its notice and site, withdrawals included. For a site's own records.",
  },
  {
    kind: "dct_consented_list",
    label: "Consented list for the Data Collection Tool",
    hint: "The file the DCT loads to tag consented people in each captured file. Valid for a week by default.",
  },
];

/** Who was left off the DCT's list, in words, or nothing if nobody was. */
function leftOut(result: ExportCreated): string {
  const l = result.left_out;
  if (!l) return "";
  const parts = [
    l.withdrawn && `${l.withdrawn} withdrawn`,
    l.partial && `${l.partial} who refused a purpose`,
    l.lapsed && `${l.lapsed} whose consent has lapsed`,
    l.no_name && `${l.no_name} with no name on record`,
  ].filter(Boolean);
  return parts.length ? ` Left off: ${parts.join(", ")}.` : "";
}

export function ExportForm({
  projectUuid,
  onDone,
  dct = true,
}: {
  projectUuid: string;
  onDone: () => void;
  /** Offer the Data Collection Tool's list. Not for HR activities, which no
   *  collection tool tags. */
  dct?: boolean;
}) {
  const toast = useToast();
  const create = useCreateExport(projectUuid);
  const [kind, setKind] = React.useState<ExportKind>("project_export");
  const [error, setError] = React.useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const result = await create.mutateAsync(kind);
      if (kind === "dct_consented_list") {
        toast.success(
          "Consented list generated",
          `${result.row_count} ${result.row_count === 1 ? "person" : "people"} on it.${leftOut(result)} Download it from the Exports page and load it in the DCT.`,
        );
      } else {
        toast.success(
          "Export generated",
          result.row_count === 0
            ? "Nobody has consented on this project yet, so the file carries the project details only."
            : `${result.row_count} consent(s). Download it from the Exports page — downloading is repeatable.`,
        );
      }
      onDone();
    } catch (err) {
      setError(
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "Could not generate the export.",
      );
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate>
      <FormError message={error} />

      <div className="space-y-4">
        {dct && (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">What to generate</legend>
            {KINDS.map((k) => (
              <label key={k.kind} className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="export-kind"
                  className="mt-0.5 size-4 accent-[var(--accent)]"
                  checked={kind === k.kind}
                  onChange={() => {
                    setKind(k.kind);
                    setError(null);
                  }}
                />
                <span>
                  {k.label}
                  <span className="block text-xs text-text-subtle">{k.hint}</span>
                </span>
              </label>
            ))}
          </fieldset>
        )}

        {kind === "dct_consented_list" ? (
          <>
            <Alert tone="warning">
              <p className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>
                  This CSV contains personal data — the name of every person whose consent is in force,
                  with the last two digits of their mobile — and it goes onto collection laptops. Generating
                  it writes one disclosure row each, and it cannot be undone. Delete it from the laptops once
                  the collection is exported and accepted.
                </span>
              </p>
            </Alert>
            <Alert tone="info">
              One row per person, in the Data Collection Tool&rsquo;s own format. Only people whose latest
              consent is fully in force are on it: anyone who withdrew, refused a purpose or whose consent has
              lapsed is left off, and a child or anyone whose age is not known is marked so the tool will not
              let them be tagged. No email, mobile number, link or notice is in it. It says until when it may be
              used (a week by default), and the tool tags nothing captured after that.
            </Alert>
          </>
        ) : (
          <>
            <Alert tone="warning">
              <p className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>
                  This CSV contains personal data — name, email and mobile number for every
                  person who consented. Generating it writes one disclosure row each. That
                  record is what makes &ldquo;who was my data shared with?&rdquo; answerable,
                  and it cannot be undone. If you only need another copy,{" "}
                  <strong>download the existing export</strong> instead.
                </span>
              </p>
            </Alert>

            <Alert tone="info">
              One row per consent, carrying the project, the notice version and the site
              alongside the person — so an agent can tell whom each consent is against
              without a second file. People who have withdrawn are included and marked, because
              that is the row you most need to act on.
            </Alert>
          </>
        )}
      </div>

      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={create.isPending}>
          <Download className="size-4" />
          {kind === "dct_consented_list" ? "Generate the consented list" : "Generate the export"}
        </Button>
      </DialogFooter>
    </form>
  );
}
