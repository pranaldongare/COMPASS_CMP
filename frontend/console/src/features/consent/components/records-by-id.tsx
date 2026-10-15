/**
 * Consent records by ID (2026-10-15): staff paste a list, or upload one, and
 * get exactly those records as PDFs in a ZIP.
 *
 * For a sample an auditor names, or the files a downstream store says it is
 * missing. The server answers all or none: an ID it does not find - or that
 * is not this person's to see, which it does not tell apart - refuses the
 * list, and the dialog names each one with a way to drop them and go again.
 */
"use client";

import { FileUp, ListChecks } from "lucide-react";
import * as React from "react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Alert, Button, Field, Textarea } from "@/components/ui/primitives";
import { downloadConsentRecordsByIds } from "@/features/consent/api";
import { useCanDownloadRecords } from "@/features/consent/components/consent-record";
import { consentIdsIn } from "@/features/consent/consent-ids";
import { ApiError } from "@/lib/errors/api-error";
import { saveBlob } from "@/lib/format";
import { useToast } from "@/providers";

/** One archive holds at most this many; the server says the same. */
const LIMIT = 200;

export function ConsentRecordsById() {
  const [open, setOpen] = React.useState(false);
  if (!useCanDownloadRecords()) return null;
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        <ListChecks className="size-4" />
        By consent IDs
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title="Download consent records by ID"
          description="Paste the consent IDs, or upload a list. You get one PDF per consent in a ZIP, with a manifest."
          size="lg"
        >
          <ByIdForm onDone={() => setOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}

function ByIdForm({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const file = React.useRef<HTMLInputElement>(null);
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [notFound, setNotFound] = React.useState<string[]>([]);
  const parsed = React.useMemo(() => consentIdsIn(text), [text]);
  const count = parsed.ids.length;

  async function upload(chosen: File | undefined) {
    if (!chosen) return;
    setText(await chosen.text());
    setError(null);
    setNotFound([]);
  }

  function dropNotFound() {
    const gone = new Set(notFound);
    setText(parsed.ids.filter((id) => !gone.has(id)).join("\n"));
    setNotFound([]);
    setError(null);
  }

  async function download() {
    setBusy(true);
    setError(null);
    setNotFound([]);
    try {
      const got = await downloadConsentRecordsByIds(parsed.ids);
      saveBlob(got.blob, got.filename);
      toast.success(
        `${count} consent record${count === 1 ? "" : "s"} downloaded`,
        "Each PDF is listed in manifest.csv with its SHA-256.",
      );
      onDone();
    } catch (err) {
      if (err instanceof ApiError && Array.isArray(err.details.not_found)) {
        setNotFound(err.details.not_found as string[]);
      }
      setError(
        err instanceof ApiError ? err.userMessage() : "The records could not be made.",
      );
    } finally {
      setBusy(false);
    }
  }

  const hint =
    count === 0
      ? "One ID a line, or separated by commas. A CSV with a consent_uuid column is read by that column."
      : `${count} consent ID${count === 1 ? "" : "s"}` +
        (parsed.repeats ? `, ${parsed.repeats} repeated (counted once)` : "") +
        (count > LIMIT ? `. At most ${LIMIT} at a time: split the list.` : ".");

  return (
    <div className="space-y-4">
      <Field label="Consent IDs" hint={hint}>
        {(props) => (
          <Textarea
            {...props}
            rows={8}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setNotFound([]);
              setError(null);
            }}
            placeholder={
              "46a27302-6b59-417c-bc89-a8d68895bedc\n655d1760-6f31-4c25-8766-9a16917ae116"
            }
            className="font-mono text-xs"
          />
        )}
      </Field>

      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={file}
          type="file"
          accept=".csv,.txt,text/csv,text/plain"
          className="sr-only"
          aria-label="A list of consent IDs"
          tabIndex={-1}
          onChange={(e) => void upload(e.target.files?.[0])}
        />
        <Button variant="secondary" size="sm" onClick={() => file.current?.click()}>
          <FileUp className="size-4" />
          Upload a list (.csv or .txt)
        </Button>
        <span className="text-xs text-text-subtle">From Excel: save as CSV.</span>
      </div>

      {parsed.unread.length > 0 && (
        <p className="text-xs text-warning-text">
          {parsed.unread.length} line{parsed.unread.length === 1 ? " has" : "s have"} no
          consent ID and {parsed.unread.length === 1 ? "is" : "are"} left out:{" "}
          {parsed.unread.slice(0, 3).join("; ")}
          {parsed.unread.length > 3 ? "…" : ""}
        </p>
      )}

      {error && (
        <Alert
          tone="danger"
          title={notFound.length > 0 ? "Some consent IDs were not found" : "Could not download"}
        >
          <p className="text-sm">{error}</p>
          {notFound.length > 0 && (
            <>
              <ul className="mt-2 max-h-32 space-y-0.5 overflow-y-auto font-mono text-xs">
                {notFound.map((id) => (
                  <li key={id}>{id}</li>
                ))}
              </ul>
              <Button variant="secondary" size="sm" className="mt-3" onClick={dropNotFound}>
                Remove {notFound.length === 1 ? "it" : "them"} from the list
              </Button>
            </>
          )}
        </Alert>
      )}

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button
          variant="primary"
          disabled={count === 0 || count > LIMIT}
          loading={busy}
          onClick={download}
        >
          {count > 0 && count <= LIMIT
            ? `Download ${count} record${count === 1 ? "" : "s"} (ZIP)`
            : "Download (ZIP)"}
        </Button>
      </div>
    </div>
  );
}
