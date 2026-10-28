/**
 * HR activities (ADR 0033): an HR PoC's, of the categories assigned to them,
 * or every one of the Legal office's for the Legal PoC. An HR PoC starts a
 * new one here; it is live as soon as it is created.
 */
"use client";

import { Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { FilterBar, FilterSelect, SearchBox } from "@/components/data-display/resource-list";
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
import { StatusBadge } from "@/components/ui/status";
import { useHrCategories } from "@/features/hr-categories";
import { useHrActivities } from "@/features/hr-activities";
import { ActivityWizard } from "@/features/hr-activities/components/activity-wizard";
import { formatDateTime } from "@/lib/format";
import { useAuth } from "@/providers";

export default function HrActivitiesPage() {
  const { me } = useAuth();
  const isPoc = me?.role === "hr_user";
  const [creating, setCreating] = React.useState(false);
  const [status, setStatus] = React.useState("approved");
  const [category, setCategory] = React.useState("");
  const [q, setQ] = React.useState("");
  const categories = useHrCategories();
  const activities = useHrActivities({
    status: status || undefined,
    category: category || undefined,
    q: q || undefined,
  });
  const rows = activities.data ?? [];

  const newButton = isPoc ? (
    <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
      <Plus className="size-4" />
      New activity
    </Button>
  ) : null;

  return (
    <>
      <PageHeader
        title="HR activities"
        description={
          isPoc
            ? "The activities you run. Each is live from the moment you create it, on a template version Legal approved."
            : "Every activity of the Legal office, each made from an approved template version."
        }
        actions={newButton}
      />

      <div className="space-y-4">
        <FilterBar>
          <SearchBox label="Search" placeholder="Activity name" value={q} onSubmit={setQ} />
          <FilterSelect
            label="Category"
            value={category}
            onChange={setCategory}
            options={(categories.data ?? []).map((c) => ({
              value: c.category_uuid,
              label: `${c.category_code} · ${c.name}`,
            }))}
            allLabel="Every category"
          />
          <FilterSelect
            label="Status"
            value={status}
            onChange={setStatus}
            options={[
              { value: "approved", label: "Running" },
              { value: "closed", label: "Closed" },
            ]}
            allLabel="Any status"
          />
        </FilterBar>

        {activities.isLoading ? (
          <TableSkeleton rows={4} cols={6} />
        ) : activities.error ? (
          <Alert tone="danger" title="Could not load the activities">
            {activities.error.userMessage()}
          </Alert>
        ) : rows.length === 0 ? (
          <EmptyState
            icon={<Sparkles />}
            title={q || category || status !== "approved" ? "No activities match" : "No activities yet"}
            description="An activity is one run of a category: a wellness week, a CSR drive, a background check."
            action={newButton}
          />
        ) : (
          <Table>
            <caption className="sr-only">HR activities</caption>
            <thead>
              <tr>
                <Th>Activity</Th>
                <Th>Category</Th>
                <Th>Template</Th>
                <Th>Status</Th>
                <Th>Consents</Th>
                <Th>Created</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <Tr key={a.activity_uuid}>
                  <Td>
                    <Link
                      href={`/hr-activities/${a.activity_uuid}`}
                      className="font-medium text-text hover:text-accent-text hover:underline"
                    >
                      {a.name}
                    </Link>
                  </Td>
                  <Td>
                    <Mono>{a.category_code}</Mono>
                  </Td>
                  <Td className="text-text-muted">
                    <Mono>{a.template_code}</Mono> v{a.template_version}
                  </Td>
                  <Td>
                    <StatusBadge kind="project" value={a.status} />
                  </Td>
                  <Td className="tabular text-text-muted">{a.consent_count}</Td>
                  <Td className="whitespace-nowrap text-text-muted">
                    {formatDateTime(a.created_at)}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent
          title="New HR activity"
          description="Made from a template version Legal approved. It is live, with its link, as soon as you create it."
          size="lg"
        >
          {creating && <ActivityWizard onDone={() => setCreating(false)} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
