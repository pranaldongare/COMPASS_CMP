/**
 * One HR category (0052, ADR 0033).
 *
 * What it is, the processors that hold data collected under it - each with
 * what it is to the category and who answers for it - the HR PoCs assigned
 * to run its activities, and its templates. The Legal PoC edits it; an HR PoC
 * and the administrator read it. HR PoCs are assigned on their account pages,
 * by the administrator, as a DCO's processors are.
 */
"use client";

import {
  ArrowLeft,
  Building2,
  FileStack,
  Hash,
  Pencil,
  Plus,
  Tags,
  Trash2,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { RecordHeader } from "@/components/layout/record-header";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Mono,
  Select,
  Skeleton,
  Table,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  CategoryForm,
  CategoryStatusBadge,
} from "@/features/hr-categories/components/category-form";
import {
  useHrCategory,
  useSetCategoryProcessors,
  useSetHrCategoryStatus,
} from "@/features/hr-categories";
import {
  NewTemplateButton,
  TemplatesPanel,
} from "@/features/notice-templates/components/templates-panel";
import { useAllProcessors } from "@/features/registry";
import { useStaff } from "@/features/users/queries";
import { formatDateTime, humanise } from "@/lib/format";
import { useAuth, useToast } from "@/providers";
import type { CategoryProcessorRole, HrCategoryDetail, Uuid } from "@/types";

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

const PROCESSOR_ROLES: { value: CategoryProcessorRole; label: string }[] = [
  { value: "hrms", label: "HR system of record" },
  { value: "database", label: "Database" },
  { value: "vendor", label: "Vendor" },
];

export default function HrCategoryPage() {
  const params = useParams<{ uuid: string }>();
  const { me } = useAuth();
  const category = useHrCategory(params?.uuid);
  const [editing, setEditing] = React.useState(false);
  const canWrite = me?.writes.includes("hr_category") ?? false;
  const readsTemplates = me?.nav.includes("templates") ?? false;

  if (category.isLoading) return <Skeleton className="h-96" />;
  if (category.error) {
    return (
      <Alert tone="danger" title="Could not load this category">
        {category.error.userMessage()}
      </Alert>
    );
  }
  const c = category.data;
  if (!c) return null;

  return (
    <>
      <PageHeader
        heading={false}
        breadcrumb={
          <Link
            href="/hr-categories"
            className="inline-flex items-center gap-1 hover:underline"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            HR categories
          </Link>
        }
        title={c.name}
      />
      <RecordHeader
        icon={Tags}
        title={c.name}
        meta={
          <>
            <span className="text-2xs font-semibold tracking-wider text-accent-text uppercase">
              HR category
            </span>
            <CategoryStatusBadge status={c.status} />
            <Mono className="font-semibold text-text">{c.category_code}</Mono>
          </>
        }
        actions={
          canWrite ? (
            <>
              <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="size-4" />
                Edit
              </Button>
              <RetireButton category={c} />
            </>
          ) : null
        }
        facts={[
          { label: "Code", value: c.category_code, icon: Hash, tint: 0 },
          { label: "Processors", value: c.processors.length, icon: Building2, tint: 1 },
          { label: "HR PoCs", value: c.pocs.length, icon: Users, tint: 2 },
          { label: "Templates", value: c.template_count, icon: FileStack, tint: 3 },
        ]}
      />

      <div className="space-y-5">
        {c.description && (
          <p className="max-w-3xl text-sm text-text-muted">{c.description}</p>
        )}
        {c.status === "retired" && (
          <Alert tone="info">
            <p className="text-sm">
              Retired on {formatDateTime(c.retired_at)}: it takes no new template and its
              processors are fixed. What was given under it stands.
            </p>
          </Alert>
        )}
        <div className="grid gap-5 lg:grid-cols-2 lg:items-start">
          <Processors category={c} canWrite={canWrite && c.status === "active"} />
          <Pocs category={c} />
        </div>
        {readsTemplates && (
          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-3">
              <CardTitle>Templates</CardTitle>
              {canWrite && c.status === "active" && (
                <NewTemplateButton variant="secondary" category={c.category_uuid} />
              )}
            </CardHeader>
            <CardBody>
              <TemplatesPanel category={c.category_uuid} />
            </CardBody>
          </Card>
        )}
      </div>

      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent title="Edit the category">
          <CategoryForm category={c} onDone={() => setEditing(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}

function RetireButton({ category: c }: { category: HrCategoryDetail }) {
  const toast = useToast();
  const status = useSetHrCategoryStatus(c.category_uuid);
  const retiring = c.status === "active";
  return (
    <Button
      variant={retiring ? "subtle" : "secondary"}
      size="sm"
      loading={status.isPending}
      onClick={async () => {
        try {
          await status.mutateAsync(retiring ? "retired" : "active");
          toast.success(
            retiring ? `${c.category_code} retired` : `${c.category_code} is back in use`,
            retiring ? "It takes no new template." : undefined,
          );
        } catch (err) {
          toast.error("Not done", messageOf(err, "The server refused."));
        }
      }}
    >
      {retiring ? "Retire" : "Bring back"}
    </Button>
  );
}

interface Row {
  processor_uuid: Uuid;
  processor_role: CategoryProcessorRole;
  respondent_user_uuid: Uuid | "";
}

/** The processors that hold the category's data. Edited as a whole list and
 *  saved at once: one left out is marked removed on the server, never
 *  deleted. */
function Processors({
  category: c,
  canWrite,
}: {
  category: HrCategoryDetail;
  canWrite: boolean;
}) {
  const toast = useToast();
  const save = useSetCategoryProcessors(c.category_uuid);
  const [editing, setEditing] = React.useState(false);
  const [rows, setRows] = React.useState<Row[]>([]);
  const processors = useAllProcessors();
  const staff = useStaff(editing);
  // The respondent works in the Legal office: the server refuses anybody else.
  const respondents = (staff.data ?? []).filter(
    (s) => s.role === "legal" || s.role === "hr_user",
  );
  const choosable = (processors.data ?? []).filter((p) => p.status === "active");

  function start() {
    setRows(
      c.processors.map((p) => ({
        processor_uuid: p.processor_uuid,
        processor_role: p.processor_role,
        respondent_user_uuid: p.respondent_uuid ?? "",
      })),
    );
    setEditing(true);
  }

  function change(i: number, patch: Partial<Row>) {
    setRows((current) => current.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  }

  async function submit() {
    if (rows.some((r) => !r.processor_uuid)) {
      toast.error("Not saved", "Choose a processor on every row, or remove the row.");
      return;
    }
    try {
      await save.mutateAsync(
        rows.map((r) => ({
          processor_uuid: r.processor_uuid,
          processor_role: r.processor_role,
          respondent_user_uuid: r.respondent_user_uuid || null,
        })),
      );
      toast.success("Processors saved");
      setEditing(false);
    } catch (err) {
      toast.error("Not saved", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Processors</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Who holds data collected under this category, and who answers for each on a
            request or a withdrawal. With nobody named, the activity&apos;s HR PoC answers.
          </p>
        </div>
        {canWrite && !editing && (
          <Button variant="secondary" size="sm" onClick={start}>
            <Pencil className="size-4" />
            Change
          </Button>
        )}
      </CardHeader>
      <CardBody>
        {editing ? (
          <div className="space-y-3">
            {rows.map((r, i) => (
              <div
                key={i}
                className="grid gap-2 rounded-md border border-border p-3 sm:grid-cols-3"
              >
                <Select
                  aria-label="Processor"
                  value={r.processor_uuid}
                  onChange={(e) => change(i, { processor_uuid: e.target.value })}
                >
                  <option value="">Choose a processor</option>
                  {choosable.map((p) => (
                    <option key={p.processor_uuid} value={p.processor_uuid}>
                      {p.legal_name}
                    </option>
                  ))}
                </Select>
                <Select
                  aria-label="What it is to the category"
                  value={r.processor_role}
                  onChange={(e) =>
                    change(i, { processor_role: e.target.value as CategoryProcessorRole })
                  }
                >
                  {PROCESSOR_ROLES.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </Select>
                <div className="flex gap-2">
                  <Select
                    aria-label="Who answers for it"
                    value={r.respondent_user_uuid}
                    onChange={(e) => change(i, { respondent_user_uuid: e.target.value })}
                  >
                    <option value="">The activity&apos;s HR PoC</option>
                    {respondents.map((s) => (
                      <option key={s.uuid} value={s.uuid}>
                        {s.full_name} · {humanise(s.role)}
                      </option>
                    ))}
                  </Select>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label="Remove this processor"
                    onClick={() => setRows((current) => current.filter((_, j) => j !== i))}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </div>
            ))}
            <div className="flex flex-wrap justify-between gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  setRows((current) => [
                    ...current,
                    {
                      processor_uuid: "",
                      processor_role: "vendor",
                      respondent_user_uuid: "",
                    },
                  ])
                }
              >
                <Plus className="size-4" />
                Add a processor
              </Button>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  loading={save.isPending}
                  onClick={submit}
                >
                  Save processors
                </Button>
              </div>
            </div>
          </div>
        ) : c.processors.length === 0 ? (
          <EmptyState
            icon={<Building2 />}
            title="No processors named"
            description="Name the HR system, databases and vendors that will hold this category's data."
          />
        ) : (
          <Table>
            <caption className="sr-only">Processors of {c.category_code}</caption>
            <thead>
              <tr>
                <Th>Processor</Th>
                <Th>What it is</Th>
                <Th>Answers for it</Th>
              </tr>
            </thead>
            <tbody>
              {c.processors.map((p) => (
                <Tr key={p.processor_uuid}>
                  <Td>
                    {p.legal_name}
                    {p.processor_status !== "active" && (
                      <span className="text-xs text-text-muted">
                        {" "}
                        · {p.processor_status}
                      </span>
                    )}
                  </Td>
                  <Td>
                    {PROCESSOR_ROLES.find((o) => o.value === p.processor_role)?.label}
                  </Td>
                  <Td className="text-text-muted">
                    {p.respondent_name ?? "The activity's HR PoC"}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </CardBody>
    </Card>
  );
}

function Pocs({ category: c }: { category: HrCategoryDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>HR PoCs</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Who may run this category&apos;s activities. The administrator assigns them on
          each HR PoC&apos;s account page.
        </p>
      </CardHeader>
      <CardBody>
        {c.pocs.length === 0 ? (
          <p className="text-sm text-text-muted">Nobody is assigned yet.</p>
        ) : (
          <ul className="divide-y divide-border text-sm">
            {c.pocs.map((p) => (
              <li key={p.uuid} className="flex flex-wrap justify-between gap-2 py-2">
                <span>
                  {p.full_name}
                  {p.email && <span className="text-text-muted"> · {p.email}</span>}
                </span>
                <span className="text-xs text-text-muted">
                  since {formatDateTime(p.assigned_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
