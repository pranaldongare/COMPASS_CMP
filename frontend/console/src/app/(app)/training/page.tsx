/**
 * Training (2026-11-24): the signed-in person's course, module by module.
 *
 * Only once signed in - the route is not public, and the server grants the
 * section to every staff role. Which modules a person sees is their role's;
 * where they are in each is kept in their browser (`useTrainingProgress`).
 */
"use client";

import {
  ArrowRight,
  CheckCircle2,
  Circle,
  Clock,
  ListChecks,
  PlayCircle,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { Badge, Card, CardBody, EmptyState } from "@/components/ui/primitives";
import { statusLabel } from "@/components/ui/status";
import { modulesFor, type TrainingModule } from "@/features/training/content";
import {
  shareOf,
  stateOf,
  useTrainingProgress,
  type ModuleProgress,
  type ModuleState,
} from "@/features/training/progress";
import { cn } from "@/lib/format";
import { useAuth } from "@/providers";

const STATE: Record<
  ModuleState,
  { label: string; tone: "neutral" | "accent" | "success"; cta: string }
> = {
  "not-started": { label: "Not started", tone: "neutral", cta: "Start" },
  "in-progress": { label: "In progress", tone: "accent", cta: "Continue" },
  complete: { label: "Complete", tone: "success", cta: "Review" },
};

export default function TrainingPage() {
  const { me } = useAuth();
  const modules = modulesFor(me?.role);
  const { progress } = useTrainingProgress(me?.uuid);

  const complete = modules.filter((m) => stateOf(m, progress[m.id]) === "complete").length;
  const minutes = modules.reduce((sum, m) => sum + m.minutes, 0);
  const next = modules.find((m) => stateOf(m, progress[m.id]) !== "complete");
  const share = modules.length ? complete / modules.length : 0;

  return (
    <>
      <PageHeader title="Training" />

      {modules.length === 0 ? (
        <EmptyState
          icon={<ListChecks className="size-6" aria-hidden="true" />}
          title="No training for this role yet"
          description="The Help manual covers everything your role can do."
        />
      ) : (
        <div className="space-y-6">
          <Card>
            <CardBody className="flex flex-wrap items-center gap-x-8 gap-y-4">
              <div className="min-w-0 flex-1 basis-72">
                <p className="text-xs font-semibold tracking-wider text-accent-text uppercase">
                  Your course · {statusLabel("role", me?.role)}
                </p>
                <h2 className="mt-1 text-lg font-semibold text-text">
                  {complete === modules.length
                    ? "You have completed every module"
                    : `${complete} of ${modules.length} modules complete`}
                </h2>
                <p className="mt-1 text-sm text-text-muted">
                  {modules.length} modules, about {minutes} minutes in all. Each walks
                  through the work step by step and ends with a few questions.
                </p>
                <div
                  className="mt-3 h-2 overflow-hidden rounded-full bg-bg-inset"
                  role="progressbar"
                  aria-label="Course progress"
                  aria-valuemin={0}
                  aria-valuemax={modules.length}
                  aria-valuenow={complete}
                  aria-valuetext={`${complete} of ${modules.length} modules complete`}
                >
                  <div
                    className="h-full rounded-full bg-accent transition-[width]"
                    style={{ width: `${Math.round(share * 100)}%` }}
                  />
                </div>
              </div>
              {next && (
                <Link
                  href={`/training/${next.id}`}
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-accent-contrast hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
                >
                  <PlayCircle className="size-4" aria-hidden="true" />
                  {stateOf(next, progress[next.id]) === "in-progress"
                    ? "Continue"
                    : "Start"}
                  : {next.title}
                </Link>
              )}
            </CardBody>
          </Card>

          <ol
            className="grid [grid-template-columns:repeat(auto-fill,minmax(18rem,1fr))] gap-4"
            aria-label="Modules"
          >
            {modules.map((m, i) => (
              <li key={m.id}>
                <ModuleCard mod={m} index={i} progress={progress[m.id]} />
              </li>
            ))}
          </ol>
        </div>
      )}
    </>
  );
}

function ModuleCard({
  mod,
  index,
  progress,
}: {
  mod: TrainingModule;
  index: number;
  progress: ModuleProgress | undefined;
}) {
  const state = stateOf(mod, progress);
  const s = STATE[state];
  const share = shareOf(mod, progress);
  return (
    <Link
      href={`/training/${mod.id}`}
      className={cn(
        "group flex h-full flex-col gap-3 rounded-xl border border-border bg-surface p-4 transition-colors",
        "hover:border-accent-border hover:bg-surface-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs font-medium text-text-subtle">Module {index + 1}</span>
        <Badge tone={s.tone}>
          {state === "complete" ? (
            <CheckCircle2 className="size-3.5" aria-hidden="true" />
          ) : (
            <Circle className="size-3.5" aria-hidden="true" />
          )}
          {s.label}
        </Badge>
      </div>
      <div>
        <h3 className="font-semibold text-text">{mod.title}</h3>
        <p className="mt-1 text-sm text-text-muted">{mod.summary}</p>
      </div>
      <div className="mt-auto space-y-2">
        <div className="h-1.5 overflow-hidden rounded-full bg-bg-inset" aria-hidden="true">
          <div
            className="h-full rounded-full bg-accent"
            style={{ width: `${Math.round(share * 100)}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-text-muted">
          <span className="inline-flex items-center gap-1.5">
            <Clock className="size-3.5" aria-hidden="true" />
            {mod.minutes} min · {mod.steps.length} steps
          </span>
          <span className="inline-flex items-center gap-1 font-semibold text-accent-text">
            {s.cta}
            <ArrowRight
              className="size-3.5 transition-transform group-hover:translate-x-0.5"
              aria-hidden="true"
            />
          </span>
        </div>
      </div>
    </Link>
  );
}
