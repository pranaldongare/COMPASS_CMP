/**
 * Narrow a list to one project (2026-10-09): every project in scope, by name.
 * One control, used by every register that spans projects - approvals,
 * consents, consent links, collection sites.
 */
"use client";

import { FilterSelect } from "@/components/data-display/resource-list";
import { useProjects } from "@/features/projects/queries";

export function ProjectFilter({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const projects = useProjects({ limit: 200 });
  return (
    <FilterSelect
      label="Project"
      value={value}
      onChange={onChange}
      options={(projects.data?.items ?? []).map((p) => ({ value: p.project_uuid, label: p.project_name }))}
      allLabel="All projects"
    />
  );
}
