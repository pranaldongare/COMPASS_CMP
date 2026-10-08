/**
 * The consent register.
 *
 * Staff see consent status and contact details, and no other personal data.
 * Every status here is derived from `v_current_consent` on read - a stored
 * status column would be a second copy of the truth, and the copy goes stale
 * the moment somebody withdraws.
 */
"use client";

import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  FilterBar,
  FilterSelect,
  ResourceList,
  useCursorStack,
  useFilterParam,
} from "@/components/data-display/resource-list";
import { EmptyConsent } from "@/components/ui/graphics";
import { Button, Field, Input, Td, Tr } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useAllConsents } from "@/features/consent";
import { useProjects, useSites } from "@/features/projects";
import type { ConsentListRow } from "@/types";
import { formatDateTime } from "@/lib/format";

/** Not from /meta/enums: these are derived states, not a database enum. */
const STATUS_OPTIONS = [
  { value: "consented", label: "Full - every purpose" },
  { value: "partial", label: "Partial - some purposes" },
  { value: "declined", label: "Declined - no purpose" },
  { value: "withdrawn", label: "Withdrawn" },
];

function ConsentsPageView() {
  const stack = useCursorStack();
  const [status, setStatus] = useFilterParam("status");
  // By project, its site, and when it was given (2026-10-08).
  const [project, setProject] = useFilterParam("project");
  const [site, setSite] = useFilterParam("site");
  const [from, setFrom] = useFilterParam("from");
  const [to, setTo] = useFilterParam("to");
  const projects = useProjects({ limit: 200 });
  const sites = useSites(project || undefined);
  const filtered = Boolean(status || project || site || from || to);

  const query = useAllConsents({
    status: status || undefined,
    project: project || undefined,
    site: site || undefined,
    // Whole days: from the start of the first to the end of the last.
    from: from ? `${from}T00:00:00` : undefined,
    to: to ? `${to}T23:59:59` : undefined,
    cursor: stack.cursor,
    limit: 25,
  });

  function set(apply: () => void) {
    apply();
    stack.reset();
  }

  return (
    <>
      <PageHeader
        title="Consents"
        description="The current position for every data subject in scope. Withdrawal supersedes rather than edits, so this always reflects the latest artefact."
      />

      <FilterBar>
        <FilterSelect
          label="Project"
          value={project}
          onChange={(v) =>
            set(() => {
              setProject(v);
              setSite("");
            })
          }
          options={(projects.data?.items ?? []).map((p) => ({ value: p.project_uuid, label: p.project_name }))}
          allLabel="All projects"
        />
        <FilterSelect
          label="Site"
          value={site}
          onChange={(v) => set(() => setSite(v))}
          options={(project ? (sites.data ?? []) : []).map((s) => ({ value: s.site_uuid, label: s.site_label }))}
          allLabel={project ? "All sites" : "Choose a project first"}
        />
        <FilterSelect
          label="Status"
          value={status}
          onChange={(v) => set(() => setStatus(v))}
          options={STATUS_OPTIONS}
          allLabel="All statuses"
        />
        <div className="w-40">
          <Field label="Given from">
            {(p) => (
              <Input {...p} type="date" value={from} max={to || undefined} onChange={(e) => set(() => setFrom(e.target.value))} />
            )}
          </Field>
        </div>
        <div className="w-40">
          <Field label="Given to">
            {(p) => (
              <Input {...p} type="date" value={to} min={from || undefined} onChange={(e) => set(() => setTo(e.target.value))} />
            )}
          </Field>
        </div>
        {filtered && (
          <div className="self-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                set(() => {
                  setStatus("");
                  setProject("");
                  setSite("");
                  setFrom("");
                  setTo("");
                })
              }
            >
              Clear filters
            </Button>
          </div>
        )}
      </FilterBar>

      <ResourceList<ConsentListRow>
        query={query}
        stack={stack}
        caption="Current consent records across all projects in scope"
        columns={["Data subject", "Project", "Site", "Status", "Purposes", "Recorded"]}
        keyOf={(c) => c.consent_uuid}
        empty={{
          illustration: <EmptyConsent />,
          title: filtered ? "No consents match" : "No consent records yet",
          description:
            "Records appear once a data subject completes a consent link for an approved project.",
        }}
        row={(c) => (
          <Tr>
            <Td>
              <Link
                href={`/consents/${c.consent_uuid}`}
                className="font-medium text-accent-text hover:underline"
              >
                {c.subject_name}
              </Link>
              <p className="mt-0.5 text-xs text-text-subtle">{c.subject_email}</p>
            </Td>
            <Td>
              <Link
                href={`/projects/${c.project_uuid}`}
                className="text-text-muted hover:text-text hover:underline"
              >
                {c.project_name}
              </Link>
            </Td>
            <Td className="text-text-muted">{c.site_label}</Td>
            <Td>
              <StatusBadge kind="consent" value={c.consent_status} />
            </Td>
            <Td className="tabular text-text-muted">
              {c.granted_count} of {c.granted_count + c.refused_count}
            </Td>
            <Td className="whitespace-nowrap text-text-muted">
              {formatDateTime(c.affirmative_action_at)}
            </Td>
          </Tr>
        )}
      />
    </>
  );
}

/**
 * `useFilterParam` reads the query string, which forces client rendering, so
 * Next requires a suspense boundary around it. Without one the whole route bails
 * out of prerendering.
 */
export default function ConsentsPage() {
  return (
    <React.Suspense fallback={<PageSkeleton />}>
      <ConsentsPageView />
    </React.Suspense>
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="shimmer h-8 w-64 rounded-lg" />
      <div className="shimmer h-14 rounded-xl" />
      <div className="shimmer h-72 rounded-xl" />
    </div>
  );
}
