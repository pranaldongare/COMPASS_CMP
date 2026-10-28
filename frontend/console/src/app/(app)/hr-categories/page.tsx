/**
 * HR categories (0052, ADR 0033): the kinds of HR activity the Legal office
 * governs - wellness, CSR, background verification.
 *
 * The Legal PoC writes them and names the processors on each; an HR PoC sees
 * the ones assigned to them; the administrator sees all, to assign HR PoCs on
 * their account pages.
 */
"use client";

import { Plus, Tags } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  FilterBar,
  FilterSelect,
  SearchBox,
} from "@/components/data-display/resource-list";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  Alert,
  Button,
  EmptyState,
  Mono,
  Table,
  TableSkeleton,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import {
  CategoryForm,
  CategoryStatusBadge,
} from "@/features/hr-categories/components/category-form";
import { useHrCategories } from "@/features/hr-categories";
import { formatDateTime } from "@/lib/format";
import { useAuth } from "@/providers";

export default function HrCategoriesPage() {
  const { me } = useAuth();
  const router = useRouter();
  const canWrite = me?.writes.includes("hr_category") ?? false;
  const [creating, setCreating] = React.useState(false);
  const [status, setStatus] = React.useState("active");
  const [q, setQ] = React.useState("");
  const categories = useHrCategories({ status: status || undefined, q: q || undefined });
  const rows = categories.data ?? [];

  const newButton = canWrite ? (
    <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
      <Plus className="size-4" />
      New category
    </Button>
  ) : null;

  return (
    <>
      <PageHeader
        title="HR categories"
        description={
          me?.role === "hr_user"
            ? "The kinds of HR activity you are assigned to run."
            : "The kinds of HR activity the Legal office governs. Each holds its templates and names the processors that hold its data."
        }
        actions={newButton}
      />

      <div className="space-y-4">
        <FilterBar>
          <SearchBox label="Search" placeholder="Code or name" value={q} onSubmit={setQ} />
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

        {categories.isLoading ? (
          <TableSkeleton rows={4} cols={6} />
        ) : categories.error ? (
          <Alert tone="danger" title="Could not load the categories">
            {categories.error.userMessage()}
          </Alert>
        ) : rows.length === 0 ? (
          <EmptyState
            icon={<Tags />}
            title={q || status !== "active" ? "No categories match" : "No categories yet"}
            description={
              me?.role === "hr_user"
                ? "You are not assigned to a category yet. The administrator assigns them."
                : "A category is a kind of HR activity: wellness, CSR, background verification."
            }
            action={newButton}
          />
        ) : (
          <Table>
            <caption className="sr-only">HR categories</caption>
            <thead>
              <tr>
                <Th>Code</Th>
                <Th>Name</Th>
                <Th>Status</Th>
                <Th>Processors</Th>
                <Th>HR PoCs</Th>
                <Th>Templates</Th>
                <Th>Updated</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <Tr key={c.category_uuid}>
                  <Td>
                    <Link
                      href={`/hr-categories/${c.category_uuid}`}
                      className="font-medium text-text hover:text-accent-text hover:underline"
                    >
                      <Mono>{c.category_code}</Mono>
                    </Link>
                  </Td>
                  <Td>{c.name}</Td>
                  <Td>
                    <CategoryStatusBadge status={c.status} />
                  </Td>
                  <Td className="tabular text-text-muted">{c.processor_count}</Td>
                  <Td className="tabular text-text-muted">{c.poc_count}</Td>
                  <Td className="tabular text-text-muted">{c.template_count}</Td>
                  <Td className="whitespace-nowrap text-text-muted">
                    {formatDateTime(c.updated_at)}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent
          title="New HR category"
          description="A kind of HR activity. Its code is how templates, activities and the audit trail name it, and it does not change."
        >
          <CategoryForm
            onDone={(saved) => {
              setCreating(false);
              if (saved) router.push(`/hr-categories/${saved.category_uuid}`);
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
