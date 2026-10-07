/**
 * Documents she sends with a request (2026-10-07): a proof of who she is, a
 * letter, a screenshot of what she is complaining about.
 *
 * Chosen here, before the request exists, and sent once it is recorded - the
 * clock runs from the request, not from the uploads. What the API would refuse
 * (too large, a type it does not take, more than ten) is said here instead,
 * before anything is sent. A file chosen in error is taken off the list; once
 * sent, a document is kept as it came.
 */
"use client";

import { Paperclip, Plus, X } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/primitives";
import {
  DOCUMENT_ACCEPT,
  DOCUMENT_MAX_BYTES,
  DOCUMENT_MAX_COUNT,
} from "@/features/rights/api";
import { formatBytes } from "@/lib/format";

const ALLOWED = DOCUMENT_ACCEPT.split(",");

function allowed(file: File): boolean {
  const name = file.name.toLowerCase();
  return ALLOWED.some((ext) => name.endsWith(ext));
}

export function DocumentPicker({
  files,
  onChange,
}: {
  files: File[];
  onChange: (next: File[]) => void;
}) {
  const id = React.useId();
  const input = React.useRef<HTMLInputElement>(null);
  const [problem, setProblem] = React.useState<string | null>(null);
  const full = files.length >= DOCUMENT_MAX_COUNT;

  function add(chosen: FileList | null) {
    if (!chosen) return;
    const next = [...files];
    const refused: string[] = [];
    for (const file of Array.from(chosen)) {
      if (!allowed(file)) refused.push(`${file.name} is not a PDF, image, text or Word file`);
      else if (file.size === 0) refused.push(`${file.name} is empty`);
      else if (file.size > DOCUMENT_MAX_BYTES)
        refused.push(`${file.name} is ${formatBytes(file.size)}; the limit is 25 MB`);
      else if (next.length >= DOCUMENT_MAX_COUNT)
        refused.push(`${file.name} was not added: ${DOCUMENT_MAX_COUNT} documents at most`);
      else next.push(file);
    }
    setProblem(refused.length ? `${refused.join(". ")}.` : null);
    onChange(next);
    if (input.current) input.current.value = "";
  }

  return (
    <div className="space-y-2">
      <div>
        <p id={`${id}-label`} className="text-sm font-medium text-text">
          Documents <span className="font-normal text-text-subtle">(optional)</span>
        </p>
        <p id={`${id}-hint`} className="text-xs text-text-subtle">
          Anything that helps us act on it - a proof of who you are, a letter, a screenshot. PDF,
          image, text or Word; up to {DOCUMENT_MAX_COUNT} files, 25 MB each.
        </p>
      </div>

      {files.length > 0 && (
        <ul className="space-y-1" aria-labelledby={`${id}-label`}>
          {files.map((file, i) => (
            <li
              key={`${file.name}-${i}`}
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
                onClick={() => onChange(files.filter((_, j) => j !== i))}
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
        accept={DOCUMENT_ACCEPT}
        className="sr-only"
        aria-describedby={`${id}-hint`}
        onChange={(e) => add(e.target.files)}
        tabIndex={-1}
      />
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={full}
        onClick={() => input.current?.click()}
      >
        <Plus className="size-4" />
        {files.length ? "Add more documents" : "Add documents"}
      </Button>

      {problem && (
        <p role="alert" className="text-xs text-danger-text">
          {problem}
        </p>
      )}
    </div>
  );
}
