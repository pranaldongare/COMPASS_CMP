/**
 * The documents that go out with a response or a refusal (2026-11-12): an
 * extract a holder returned, a corrected document, the letter a refusal
 * rests on.
 *
 * A button that reads as one. The browser's own "Choose files" was a small
 * grey control under the response, and the officer did not see that a file
 * could go with it. What the server would refuse - too large, a kind it does
 * not take - is said here, before anything is sent; a file chosen in error
 * comes off the list.
 */
"use client";

import { Paperclip, Upload, X } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/primitives";
import { formatBytes } from "@/lib/format";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.csv,.txt";
const MAX_BYTES = 25 * 1024 * 1024;
const TYPES = ACCEPT.split(",");

export function ReleaseFiles({
  label,
  hint,
  files,
  onChange,
}: {
  label: string;
  hint: string;
  files: File[];
  onChange: (next: File[]) => void;
}) {
  const id = React.useId();
  const input = React.useRef<HTMLInputElement>(null);
  const [problem, setProblem] = React.useState<string | null>(null);

  function add(chosen: FileList | null) {
    if (!chosen) return;
    const next = [...files];
    const refused: string[] = [];
    for (const file of Array.from(chosen)) {
      const name = file.name.toLowerCase();
      if (!TYPES.some((ext) => name.endsWith(ext)))
        refused.push(`${file.name} is not a PDF, image, CSV or text file`);
      else if (file.size === 0) refused.push(`${file.name} is empty`);
      else if (file.size > MAX_BYTES)
        refused.push(`${file.name} is ${formatBytes(file.size)}; the limit is 25 MB`);
      else if (!next.some((o) => o.name === file.name && o.size === file.size)) next.push(file);
    }
    setProblem(refused.length ? `${refused.join(". ")}.` : null);
    onChange(next);
    // The same file chosen again after being taken off is a choice too.
    if (input.current) input.current.value = "";
  }

  return (
    <div className="space-y-2">
      <div>
        <p id={`${id}-label`} className="text-sm font-medium text-text">
          {label} <span className="font-normal text-text-subtle">(optional)</span>
        </p>
        <p id={`${id}-hint`} className="text-xs text-text-subtle">
          {hint}
        </p>
      </div>

      {files.length > 0 && (
        <ul className="space-y-1" aria-labelledby={`${id}-label`}>
          {files.map((file) => (
            <li
              key={`${file.name}-${file.size}`}
              className="flex items-center gap-2 rounded-md border border-border bg-bg-inset px-3 py-1.5 text-sm"
            >
              <Paperclip className="size-3.5 shrink-0 text-text-subtle" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate">{file.name}</span>
              <span className="shrink-0 text-xs text-text-muted">{formatBytes(file.size)}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-label={`Remove ${file.name}`}
                onClick={() => onChange(files.filter((o) => o !== file))}
              >
                <X className="size-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <input
        ref={input}
        id={id}
        type="file"
        multiple
        accept={`${ACCEPT},application/pdf,image/png,image/jpeg,text/csv,text/plain`}
        className="sr-only"
        aria-labelledby={`${id}-label`}
        aria-describedby={`${id}-hint`}
        onChange={(e) => add(e.target.files)}
        tabIndex={-1}
      />
      <Button type="button" variant="secondary" onClick={() => input.current?.click()}>
        <Upload className="size-4" />
        {files.length ? "Attach more files" : "Attach files"}
      </Button>

      {problem && (
        <p role="alert" className="text-xs text-danger-text">
          {problem}
        </p>
      )}
    </div>
  );
}
