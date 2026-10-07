/**
 * Who a breach touched, from a list somebody sends us (2026-10-07).
 *
 * When the people are not on the platform the records cannot list them, and
 * the breach could not close: the notice is owed to everyone listed. The list
 * comes from outside instead, from one of two templates - people by name,
 * email and mobile, or asset IDs - and is checked before it is taken: nothing
 * is written, everything it would add is counted, and every row that cannot
 * be read is named by its row number. Somebody already on the platform joins
 * the list as themselves; anybody else is kept, sealed, as this breach's
 * contact, and is sent the notice by email and SMS.
 */
"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileUp, Upload, UserX } from "lucide-react";
import * as React from "react";

import { FormError } from "@/components/forms";
import {
  Alert,
  Badge,
  Button,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  breachListTemplate,
  checkBreachList,
  listBreachContacts,
  takeBreachList,
} from "@/features/breach/api";
import { messageOf } from "@/features/breach/components/record-breach";
import { formatDateTime, saveBlob } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";
import type { Breach, BreachListKind, BreachListReport } from "@/types";

const KINDS: Record<BreachListKind, { label: string; hint: string }> = {
  contacts: {
    label: "People: name, email, mobile",
    hint: "Each person is sent the notice by email and by SMS. Somebody already on the platform is matched by email or mobile and also sees it in their account.",
  },
  assets: {
    label: "Asset IDs",
    hint: "The platform's asset ID or the capture tool's own. The people who consented in each asset are listed; people in an asset who consented to nothing cannot be traced, and are counted.",
  },
};

function Counts({ report, taken }: { report: BreachListReport; taken: boolean }) {
  const rows: [string, number][] = [
    ["Rows read", report.rows_read],
    [taken ? "On the platform, now listed" : "On the platform, to be listed", report.matched_people],
    [taken ? "Not on the platform, now listed" : "Not on the platform, to be listed", report.new_contacts],
    ["Already listed or repeated - skipped", report.already_listed],
    ["Could not be read", report.unreadable],
  ];
  if (report.kind === "assets") {
    rows.push(["In the assets but consented to nothing - cannot be traced", report.untraceable]);
  }
  return (
    <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm">
      {rows.map(([label, n]) => (
        <React.Fragment key={label}>
          <dt className="text-text-muted">{label}</dt>
          <dd className="text-right font-medium tabular">{n}</dd>
        </React.Fragment>
      ))}
    </dl>
  );
}

/** Check a filled-in template, then add what it names. */
export function UploadList({ breach, onDone }: { breach: Breach; onDone: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const input = React.useRef<HTMLInputElement>(null);
  const [kind, setKind] = React.useState<BreachListKind>("contacts");
  const [file, setFile] = React.useState<File | null>(null);
  const [report, setReport] = React.useState<BreachListReport | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<"template" | "check" | "take" | null>(null);

  function choose(next: BreachListKind) {
    setKind(next);
    setReport(null);
    setError(null);
  }

  async function template() {
    setBusy("template");
    try {
      const got = await breachListTemplate(breach.breach_uuid, kind);
      saveBlob(got.blob, got.filename);
    } catch (err) {
      toast.error("Could not download", messageOf(err, "The server refused."));
    } finally {
      setBusy(null);
    }
  }

  async function check() {
    if (!file) return;
    setBusy("check");
    setError(null);
    setReport(null);
    try {
      setReport(await checkBreachList(breach.breach_uuid, kind, file));
    } catch (err) {
      setError(messageOf(err, "The file could not be checked."));
    } finally {
      setBusy(null);
    }
  }

  async function take() {
    if (!file) return;
    setBusy("take");
    setError(null);
    try {
      const taken = await takeBreachList(breach.breach_uuid, kind, file);
      const added = taken.matched_people + taken.new_contacts;
      toast.success(
        `${added} ${added === 1 ? "person" : "people"} added to the list`,
        "Send the approved notice to reach them: email and SMS, and the account of anyone on the platform.",
      );
      void qc.invalidateQueries({ queryKey: keys.breach.affected(breach.breach_uuid) });
      void qc.invalidateQueries({ queryKey: keys.breach.notices(breach.breach_uuid) });
      void qc.invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid) });
      onDone();
    } catch (err) {
      setError(messageOf(err, "The list was not taken."));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4 rounded-md border border-border p-4">
      <div>
        <p className="text-sm font-medium">Add people from a list</p>
        <p className="mt-0.5 text-xs text-text-muted">
          For people the records cannot show - not on the platform, or known only by the assets
          they are in. Start from the template, fill it in, and check it before adding it.
        </p>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">What the list holds</legend>
        {(Object.keys(KINDS) as BreachListKind[]).map((k) => (
          <label key={k} className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              name="breach-list-kind"
              className="mt-0.5 size-4 accent-[var(--accent)]"
              checked={kind === k}
              onChange={() => choose(k)}
            />
            <span>
              {KINDS[k].label}
              <span className="block text-xs text-text-subtle">{KINDS[k].hint}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="sm" loading={busy === "template"} onClick={template}>
          <Download className="size-4" />
          Download the template
        </Button>
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          aria-label="The filled-in list"
          tabIndex={-1}
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setReport(null);
            setError(null);
          }}
        />
        <Button variant="secondary" size="sm" onClick={() => input.current?.click()}>
          <FileUp className="size-4" />
          {file ? "Choose another file" : "Choose the filled-in file"}
        </Button>
        {file && <span className="text-xs text-text-muted">{file.name}</span>}
      </div>
      <p className="text-xs text-text-subtle">
        A CSV. From Excel: File &gt; Save As &gt; CSV UTF-8. Up to 50,000 rows and 25 MB.
      </p>

      <FormError message={error} />

      {report && (
        <div className="space-y-3 rounded-md bg-bg-inset p-3">
          <Counts report={report} taken={false} />
          {report.errors.length > 0 && (
            <details open={report.would_add === 0}>
              <summary className="cursor-pointer text-sm font-medium text-warning-text">
                Rows that could not be read ({report.unreadable})
              </summary>
              <ul className="mt-2 max-h-48 space-y-0.5 overflow-y-auto text-xs">
                {report.errors.map((e) => (
                  <li key={`${e.row}:${e.message}`}>
                    Row {e.row}: {e.message}
                  </li>
                ))}
                {report.more_errors > 0 && <li>…and {report.more_errors} more</li>}
              </ul>
            </details>
          )}
          {report.would_add === 0 ? (
            <Alert tone="warning">
              <p className="text-sm">
                Nothing in this file would be added
                {report.already_listed ? ": everybody in it is already listed." : "."}
              </p>
            </Alert>
          ) : (
            report.unreadable > 0 && (
              <p className="text-xs text-text-muted">
                Adding it takes the rows that can be read. Correct the others and send the file
                again - rows already listed are skipped.
              </p>
            )
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" size="sm" onClick={onDone}>
          Cancel
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={!file}
          loading={busy === "check"}
          onClick={check}
        >
          Check the file
        </Button>
        <Button
          variant="primary"
          size="sm"
          disabled={!report || report.would_add === 0}
          loading={busy === "take"}
          onClick={take}
        >
          <Upload className="size-4" />
          {report && report.would_add > 0
            ? `Add ${report.would_add} to the list`
            : "Add to the list"}
        </Button>
      </div>
    </div>
  );
}

/** People the breach touched who have no account, and the lists they came in. */
export function BreachContacts({ breach }: { breach: Breach }) {
  const query = useQuery({
    queryKey: keys.breach.contacts(breach.breach_uuid),
    queryFn: () => listBreachContacts(breach.breach_uuid),
  });
  const data = query.data;
  const [more, setMore] = React.useState<{
    from: typeof data;
    rows: NonNullable<typeof data>["contacts"];
    cursor: string | null;
  }>({ from: undefined, rows: [], cursor: null });
  const paging = more.from === data ? more : { from: data, rows: [], cursor: data?.next_cursor ?? null };

  async function loadMore() {
    if (!paging.cursor) return;
    const page = await listBreachContacts(breach.breach_uuid, paging.cursor);
    setMore({ from: data, rows: [...paging.rows, ...page.contacts], cursor: page.next_cursor });
  }

  if (!data || (data.total === 0 && data.uploads.length === 0)) return null;
  const rows = [...data.contacts, ...paging.rows];
  return (
    <div className="space-y-3">
      <p className="flex items-center gap-2 text-sm">
        <UserX className="size-4 text-text-subtle" aria-hidden="true" />
        <span>
          <strong>{data.total}</strong> not on the platform - told by email and SMS.
        </span>
      </p>
      {rows.length > 0 && (
        <Table>
          <caption className="sr-only">People with no account</caption>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Email</Th>
              <Th>Mobile</Th>
              <Th>From</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <Tr key={c.contact_uuid}>
                <Td>{c.full_name ?? <span className="text-text-subtle">No name</span>}</Td>
                <Td className="text-sm break-all">{c.email ?? "—"}</Td>
                <Td className="text-sm whitespace-nowrap">{c.mobile ?? "—"}</Td>
                <Td className="text-sm">
                  <Badge tone="neutral">{c.upload_kind === "assets" ? "Asset list" : "People list"}</Badge>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
      {paging.cursor && (
        <Button variant="ghost" size="sm" onClick={loadMore}>
          Show more
        </Button>
      )}
      {data.uploads.length > 0 && (
        <details>
          <summary className="cursor-pointer text-xs text-text-muted">
            Lists taken ({data.uploads.length})
          </summary>
          <ul className="mt-2 space-y-1 text-xs text-text-muted">
            {data.uploads.map((u) => (
              <li key={u.upload_uuid}>
                {formatDateTime(u.added_at)} · {u.file_name} · {u.added_by_name ?? "unknown"}: {u.rows_read} rows,{" "}
                {u.matched_people} on the platform, {u.new_contacts} not, {u.already_listed} skipped,{" "}
                {u.unreadable} unreadable
                {u.kind === "assets" && `, ${u.untraceable} untraceable`}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
