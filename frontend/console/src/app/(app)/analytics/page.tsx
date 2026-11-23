/**
 * Analytics (ADR 0045): the figures over a period against their targets, the
 * ready-made audit reports, the platform's health, the record of processing,
 * and reports made as files, kept, scheduled and mailed.
 *
 * Distinct from the dashboard, which is what needs somebody today. Which tabs
 * a person has is the catalogue's word, from the same matrix the API
 * enforces with: management reads the scorecard, the analytics, the record
 * of processing and reports, for both offices or one; an officer the same
 * for their own office, with the audit reports and data quality; the
 * administrator the audit reports, health, data quality, reports and the
 * targets; the roles that do the work, their own work and its reports.
 *
 * The tab and every filter are in the address, so a link opens the page as
 * it was. A figure withheld because it counts too few people reads "< N".
 */
"use client";

import * as React from "react";

import { useFilterParam } from "@/components/data-display/resource-list";
import { PageHeader } from "@/components/layout/app-shell";
import { Alert, Skeleton } from "@/components/ui/primitives";
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs";
import { useCatalogue } from "@/features/analytics";
import { AuditPanel } from "@/features/analytics/components/audit-panel";
import { FiguresPanel } from "@/features/analytics/components/figures-panel";
import { InventoryPanel } from "@/features/analytics/components/inventory-panel";
import { ReportsPanel } from "@/features/analytics/components/reports-panel";
import { SettingsPanel } from "@/features/analytics/components/settings-panel";
import {
  AnalyticsToolbar,
  dimsFor,
  useAnalyticsFilters,
} from "@/features/analytics/components/toolbar";
import { MakeReport } from "@/features/analytics/components/make-report";
import { periodParams } from "@/features/analytics/components/toolbar";
import { useAuth } from "@/providers";
import type { Catalogue, OfficeCode } from "@/types";

/** Each tab's name, and - for a tab of figures - the report it makes. */
const TABS: Record<string, { label: string; about: string; report?: string }> = {
  management: {
    label: "Management",
    about: "The scorecard: the figures the organisation reports on, against their targets.",
    report: "management_scorecard",
  },
  analytics: {
    label: "Analytics",
    about: "Every figure of the period, with its line and its breakdowns.",
    report: "analytics_summary",
  },
  mine: {
    label: "Your work",
    about:
      "The figures of your own work: the projects, collections or activities that are yours.",
    report: "my_analytics",
  },
  audit: {
    label: "Audit reports",
    about: "Ready-made questions of the audit trail, for a period.",
  },
  health: {
    label: "Health",
    about: "Sign-in and codes, the audit trail's checks, and the pipelines.",
    report: "health",
  },
  quality: {
    label: "Data quality",
    about: "Gaps in the registers as they stand: what is missing or out of date.",
    report: "data_quality",
  },
  inventory: { label: "Record of processing", about: "" },
  reports: { label: "Reports", about: "" },
  settings: { label: "Settings", about: "" },
};

const FIGURES = new Set(["management", "analytics", "mine", "health", "quality"]);

export default function AnalyticsPage() {
  return (
    <React.Suspense fallback={null}>
      <AnalyticsPageView />
    </React.Suspense>
  );
}

function AnalyticsPageView() {
  const catalogue = useCatalogue();
  return (
    <>
      <PageHeader title="Analytics" />
      {catalogue.isLoading ? (
        <div className="space-y-4" aria-busy="true">
          <Skeleton className="h-10 w-96 max-w-full" />
          <Skeleton className="h-44" />
        </div>
      ) : catalogue.isError ? (
        <Alert tone="danger" title="Could not open Analytics">
          {catalogue.error.userMessage()}
        </Alert>
      ) : (
        <AnalyticsTabs catalogue={catalogue.data!} />
      )}
    </>
  );
}

function AnalyticsTabs({ catalogue }: { catalogue: Catalogue }) {
  const { me } = useAuth();
  const writes = me?.writes ?? [];
  // The administrator's settings tab: offered to whoever may write them, or
  // - should the session not say - to the reader of health, who is the same
  // person today.
  const settingsTab = me
    ? writes.includes("analytics_setting")
    : catalogue.sections.includes("health");
  const tabs = React.useMemo(
    () => [
      ...catalogue.sections.filter((s) => s in TABS),
      ...(settingsTab ? ["settings"] : []),
    ],
    [catalogue.sections, settingsTab],
  );
  const [param, setTab] = useFilterParam("tab", tabs[0] ?? "");
  const tab = tabs.includes(param) ? param : (tabs[0] ?? "");
  const [filters, set] = useAnalyticsFilters();
  const toReports = React.useCallback(() => {
    if (tabs.includes("reports")) setTab("reports");
  }, [tabs, setTab]);
  // A report is offered to whoever may write one; the server keeps the kinds.
  const canWriteReports = me ? writes.includes("report") : true;

  if (tabs.length === 0) {
    return (
      <Alert tone="info" title="Nothing here for your role">
        Your role has no figures or reports to read.
      </Alert>
    );
  }

  const isFigures = FIGURES.has(tab);
  const dims = isFigures ? dimsFor(catalogue, tab) : [];
  const office = catalogue.may_choose_office ? filters.office || undefined : undefined;
  const period = periodParams(filters);
  const report = TABS[tab]?.report;
  const showToolbar = isFigures || tab === "audit" || tab === "inventory";

  return (
    <Tabs value={tab} onValueChange={setTab} label="Analytics">
      <TabList>
        {tabs.map((t) => (
          <Tab key={t} value={t}>
            {TABS[t].label}
          </Tab>
        ))}
      </TabList>

      {showToolbar && (
        <AnalyticsToolbar
          catalogue={catalogue}
          filters={filters}
          set={set}
          dims={dims}
          showCompare={isFigures}
          showPeriod={tab !== "inventory"}
          showOffice={tab !== "audit"}
        />
      )}

      {tabs.map((t) => (
        <TabPanel key={t} value={t}>
          {/* Only the open tab counts its figures: each is a query. */}
          {t === tab && (
            <>
              {FIGURES.has(t) && (
                <>
                  <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                    <p className="max-w-3xl text-sm text-text-muted">{TABS[t].about}</p>
                    {report && period && canWriteReports && (
                      <MakeReport
                        catalogue={catalogue}
                        kind={report}
                        params={{
                          ...(t === "quality" ? {} : period),
                          ...(office ? { office: office as OfficeCode } : {}),
                        }}
                        onMade={toReports}
                      />
                    )}
                  </div>
                  <FiguresPanel
                    section={t}
                    catalogue={catalogue}
                    filters={filters}
                    dims={dims}
                  />
                </>
              )}
              {t === "audit" && (
                <AuditPanel catalogue={catalogue} filters={filters} onMade={toReports} />
              )}
              {t === "inventory" && (
                <InventoryPanel catalogue={catalogue} office={office} onMade={toReports} />
              )}
              {t === "reports" && (
                <ReportsPanel catalogue={catalogue} canWrite={canWriteReports} />
              )}
              {t === "settings" && <SettingsPanel canWrite={settingsTab} />}
            </>
          )}
        </TabPanel>
      ))}
    </Tabs>
  );
}
