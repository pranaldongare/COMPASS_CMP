/**
 * The DPO's notice templates, on the Notices screen (0044).
 *
 * As many as the office wants, written before any project exists. Each has
 * an ID - `TPL-0007` - to give the study's R&D User, who attaches it to their
 * project; that makes the project's own draft notice from it.
 */
"use client";

import { FileStack, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

import { FilterBar, FilterSelect, SearchBox } from "@/components/data-display/resource-list";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  Mono,
  Table,
  TableSkeleton,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { TemplateForm } from "@/features/notice-templates/components/template-form";
import { useNoticeTemplates } from "@/features/notice-templates/queries";
import { formatDateTime } from "@/lib/format";

export function TemplateStatusBadge({ status }: { status: "active" | "retired" }) {
  return status === "active" ? (
    <Badge tone="success" dot>
      Active
    </Badge>
  ) : (
    <Badge tone="neutral" dot>
      Retired
    </Badge>
  );
}

export function NewTemplateButton() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
        <Plus className="size-4" />
        New template
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title="New notice template"
          description="A notice written before any project exists. A project uses it by its ID, which makes that project's own draft notice from it."
          size="lg"
        >
          <TemplateForm
            onDone={(saved) => {
              setOpen(false);
              if (saved) router.push(`/notices/templates/${saved.template_uuid}`);
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}

export function TemplatesPanel() {
  const [status, setStatus] = React.useState("active");
  const [q, setQ] = React.useState("");
  const templates = useNoticeTemplates({ status: status || undefined, q: q || undefined });
  const rows = templates.data ?? [];

  return (
    <div className="space-y-4">
      <Alert tone="info">
        <p className="text-sm">
          Write a notice here before the project exists. Give its ID to the study&apos;s R&amp;D
          User: on their project they choose <strong>Use a notice template</strong> and enter
          it, and the project gets its own draft notice to approve and publish. A template is
          never shown to anybody until a project uses it.
        </p>
      </Alert>

      <FilterBar>
        <SearchBox label="Search" placeholder="ID or name" value={q} onSubmit={setQ} />
        <FilterSelect
          label="Status"
          value={status}
          onChange={setStatus}
          options={[
            { value: "active", label: "Active" },
            { value: "retired", label: "Retired" },
          ]}
          allLabel="Any status"
        />
      </FilterBar>

      {templates.isLoading ? (
        <TableSkeleton rows={4} cols={6} />
      ) : templates.error ? (
        <Alert tone="danger" title="Could not load the templates">
          {templates.error.userMessage()}
        </Alert>
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<FileStack />}
          title={q || status !== "active" ? "No templates match" : "No templates yet"}
          description="A template is a notice written ahead of the projects that will use it."
          action={<NewTemplateButton />}
        />
      ) : (
        <Table>
          <caption className="sr-only">Notice templates</caption>
          <thead>
            <tr>
              <Th>ID</Th>
              <Th>Name</Th>
              <Th>Status</Th>
              <Th>Purposes</Th>
              <Th>Languages</Th>
              <Th>Used by</Th>
              <Th>Updated</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <Tr key={t.template_uuid}>
                <Td>
                  <Link
                    href={`/notices/templates/${t.template_uuid}`}
                    className="font-medium text-accent-text hover:underline"
                  >
                    <Mono>{t.template_code}</Mono>
                  </Link>
                </Td>
                <Td>{t.title}</Td>
                <Td>
                  <TemplateStatusBadge status={t.status} />
                </Td>
                <Td className="tabular text-text-muted">{t.purpose_count}</Td>
                <Td className="tabular text-text-muted">{t.language_count}</Td>
                <Td className="tabular text-text-muted">
                  {t.used_count} project{t.used_count === 1 ? "" : "s"}
                </Td>
                <Td className="whitespace-nowrap text-text-muted">
                  {formatDateTime(t.updated_at)}
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
