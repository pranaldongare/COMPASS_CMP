/**
 * Notice templates as a section of their own (0052).
 *
 * The Legal PoC's: their templates, each under one of the office's
 * categories. The DPO reaches the same list from the Notices tab; this page
 * serves either office, each reading only its own (ADR 0032).
 */
"use client";

import { PageHeader } from "@/components/layout/app-shell";
import {
  NewTemplateButton,
  TemplatesPanel,
} from "@/features/notice-templates/components/templates-panel";

export default function NoticeTemplatesPage() {
  return (
    <>
      <PageHeader
        title="Notice templates"
        description="The notices your office writes ahead of the work that will use them. Retired, never deleted."
        actions={<NewTemplateButton />}
      />
      <TemplatesPanel />
    </>
  );
}
