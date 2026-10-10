/**
 * Notices, across every project in scope.
 *
 * The column that matters is "unapproved languages". Approval is per language,
 * not once per notice - a DPO who reads English and approves eight renditions
 * has approved one - and an unapproved rendition is the single most common
 * reason a notice cannot be published.
 *
 * The DPO has a second tab here (2026-10-07): notice templates, written before
 * any project exists and attached to one by their ID.
 */
"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { useHere, withFrom } from "@/lib/navigation/return-to";
import {
  FilterBar,
  FilterSelect,
  ResourceList,
  useCursorStack,
  useFilterParam,
} from "@/components/data-display/resource-list";
import { EmptyRecords } from "@/components/ui/graphics";
import { Td, Tr } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useEnums } from "@/features/meta";
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs";
import {
  NewTemplateButton,
  TemplatesPanel,
} from "@/features/notice-templates/components/templates-panel";
import { useAllNotices } from "@/features/notices";
import { useAuth } from "@/providers";
import type { NoticeListRow } from "@/types";
import { formatDateTime } from "@/lib/format";

function NoticesPageView() {
  const { me } = useAuth();
  const isDpo = me?.role === "dpo";
  const [tab, setTab] = useFilterParam("tab", "notices");
  const description =
    "The text a data subject actually reads. Publication freezes it and its hash; a correction after that is a new version, never an edit.";

  if (!isDpo) {
    return (
      <>
        <PageHeader title="Notices" description={description} />
        <ProjectNotices />
      </>
    );
  }
  return (
    <>
      <PageHeader
        title="Notices"
        description={description}
        actions={<NewTemplateButton />}
      />
      <Tabs value={tab} onValueChange={setTab} label="Notices">
        <TabList>
          <Tab value="notices">Project notices</Tab>
          <Tab value="templates">Templates</Tab>
        </TabList>
        <TabPanel value="notices">
          <ProjectNotices />
        </TabPanel>
        <TabPanel value="templates">
          {tab === "templates" && <TemplatesPanel />}
        </TabPanel>
      </Tabs>
    </>
  );
}

function ProjectNotices() {
  const stack = useCursorStack();
  const here = useHere();
  const [status, setStatus] = useFilterParam("status");
  const [languages, setLanguages] = useFilterParam("languages");

  const { data: enums } = useEnums();
  const query = useAllNotices({
    status: status || undefined,
    languages: languages || undefined,
    cursor: stack.cursor,
    limit: 25,
  });

  return (
    <>
      <FilterBar>
        <FilterSelect
          label="Status"
          value={status}
          onChange={(v) => {
            setStatus(v);
            stack.reset();
          }}
          options={enums?.notice_status ?? []}
          allLabel="All statuses"
        />
        <FilterSelect
          label="Text"
          value={languages}
          onChange={(v) => {
            setLanguages(v);
            stack.reset();
          }}
          options={[{ value: "unapproved", label: "Awaiting approval" }]}
          allLabel="Any"
        />
      </FilterBar>

      <ResourceList<NoticeListRow>
        query={query}
        stack={stack}
        caption="Notices across all projects in scope"
        columns={["Notice", "Project", "Status", "Purposes", "Languages", "Published"]}
        keyOf={(n) => n.notice_uuid}
        empty={{
          illustration: <EmptyRecords />,
          title: status ? "No notices match" : "No notices yet",
          description:
            "A notice is created against a project, then published by the DPO once every Rule 3 element is present.",
        }}
        row={(n) => (
          <Tr>
            <Td>
              <Link
                href={withFrom(`/notices/${n.notice_uuid}`, here)}
                className="font-medium text-text hover:text-accent-text hover:underline"
              >
                {n.notice_code}
              </Link>
              <p className="mt-0.5 text-xs text-text-subtle">version {n.version}</p>
            </Td>
            <Td>
              <Link
                href={`/projects/${n.project_uuid}`}
                className="text-text-muted hover:text-text hover:underline"
              >
                {n.project_name}
              </Link>
            </Td>
            <Td>
              <StatusBadge kind="notice" value={n.status} />
            </Td>
            <Td className="tabular text-text-muted">{n.purpose_count}</Td>
            <Td>
              <span className="tabular text-text-muted">{n.language_count}</span>
              {n.unapproved_languages > 0 && (
                <span className="ml-2 inline-flex items-center gap-1 text-xs text-warning-text">
                  <AlertTriangle className="size-3" aria-hidden="true" />
                  {n.unapproved_languages} unapproved
                </span>
              )}
            </Td>
            <Td className="whitespace-nowrap text-text-muted">
              {n.published_at ? formatDateTime(n.published_at) : "—"}
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
export default function NoticesPage() {
  return (
    <React.Suspense fallback={<PageSkeleton />}>
      <NoticesPageView />
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
