/**
 * Documents the requester sent with the request (2026-10-07): a proof of who
 * they are, a letter, a screenshot.
 *
 * Kept as they came - never replaced or removed - so there is nothing to do
 * here but read them. Every download is on the request's trail. The names are
 * sealed, opened by the API client like every other personal field.
 */
"use client";

import { Download, Paperclip } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/primitives";
import { downloadRequestAttachment } from "@/features/rights/api";
import { formatBytes, formatDateTime, saveBlob } from "@/lib/format";
import { useToast } from "@/providers";
import type { RightsRequestDetail } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function RequestDocuments({ request: r }: { request: RightsRequestDetail }) {
  const toast = useToast();
  const [fetching, setFetching] = React.useState<string | null>(null);
  const documents = r.attachments ?? [];
  if (documents.length === 0) return null;

  async function download(attachmentUuid: string) {
    setFetching(attachmentUuid);
    try {
      const file = await downloadRequestAttachment(r.request_uuid, attachmentUuid);
      saveBlob(file.blob, file.filename);
    } catch (err) {
      toast.error("Could not download", messageOf(err, "The server refused."));
    } finally {
      setFetching(null);
    }
  }

  return (
    <div className="mt-4">
      <p className="text-2xs font-semibold tracking-wide text-text-subtle uppercase">
        Documents from the requester · {documents.length}
      </p>
      <ul className="mt-1 divide-y divide-border rounded-md border border-border">
        {documents.map((d) => (
          <li key={d.attachment_uuid} className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
            <Paperclip className="size-3.5 shrink-0 text-text-subtle" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate">{d.file_name}</span>
            <span className="text-xs text-text-muted">
              {formatBytes(d.size_bytes)} · {formatDateTime(d.added_at)}
            </span>
            <Button
              variant="ghost"
              size="sm"
              loading={fetching === d.attachment_uuid}
              onClick={() => download(d.attachment_uuid)}
              aria-label={`Download ${d.file_name}`}
            >
              <Download className="size-4" />
              Download
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
