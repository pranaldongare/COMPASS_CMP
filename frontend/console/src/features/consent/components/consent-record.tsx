/**
 * The consent record as a PDF (2026-10-15), for the auditor's file and the
 * store downstream of it.
 *
 * Offered to the staff who read consents in full - the DPO, a DCO, a DCO
 * Admin, an RCO - and to nobody else: the PDF names the person. The server
 * decides scope and audits every copy; these buttons only ask.
 */
"use client";

import { FileDown, FolderDown } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/primitives";
import { downloadConsentRecord, downloadConsentRecords } from "@/features/consent/api";
import { saveBlob } from "@/lib/format";
import { useToast } from "@/providers";
import { useOptionalAuth } from "@/providers/auth-provider";
import type { Uuid } from "@/types";

const RECORD_ROLES = new Set(["dpo", "dco", "dco_admin", "rco", "legal", "hr_user"]);

/** Whether the signed-in role may take consent records away as PDFs. */
export function useCanDownloadRecords(): boolean {
  // Optional: a page rendered without the provider (a test, a preview) offers
  // nothing rather than failing.
  const me = useOptionalAuth()?.me;
  return Boolean(me && RECORD_ROLES.has(me.role));
}

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

/** One record. Nothing at all for a role that may not have it. */
export function DownloadConsentRecord({ uuid }: { uuid: Uuid }) {
  return useCanDownloadRecords() ? <RecordButton uuid={uuid} /> : null;
}

function RecordButton({ uuid }: { uuid: Uuid }) {
  const toast = useToast();
  const [busy, setBusy] = React.useState(false);

  async function download() {
    setBusy(true);
    try {
      const got = await downloadConsentRecord(uuid);
      saveBlob(got.blob, got.filename);
    } catch (err) {
      toast.error("Could not make the PDF", messageOf(err, "Try again in a minute."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button variant="secondary" size="sm" loading={busy} onClick={download}>
      <FileDown className="size-4" />
      Download PDF
    </Button>
  );
}

type ArchiveFilters = { project?: string; site?: string; from?: string; to?: string };

/** Every record the filters match, in a ZIP. */
export function DownloadConsentRecords({ filters }: { filters: ArchiveFilters }) {
  return useCanDownloadRecords() ? <ArchiveButton filters={filters} /> : null;
}

function ArchiveButton({ filters }: { filters: ArchiveFilters }) {
  const toast = useToast();
  const [busy, setBusy] = React.useState(false);

  async function download() {
    setBusy(true);
    try {
      const got = await downloadConsentRecords(filters);
      saveBlob(got.blob, got.filename);
    } catch (err) {
      toast.error("Could not make the archive", messageOf(err, "Try again in a minute."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button
      variant="secondary"
      loading={busy}
      onClick={download}
      title="One PDF per consent record, withdrawals included, for the project, site and dates chosen. At most 200."
    >
      <FolderDown className="size-4" />
      Download PDFs (ZIP)
    </Button>
  );
}
