/**
 * Layout for every authenticated page.
 *
 * `RequireAuth` renders nothing until the session resolves, so a protected page
 * never flashes its contents before redirecting. A flash of a project list is a
 * disclosure, however brief.
 *
 * `RequireSection` is the second gate, and answers a different question:
 * authenticated *as whom*. The sidebar only offers what a role may use, which
 * held until something outside the sidebar produced a URL — a notification
 * linking a data principal to `/users` did exactly that. Neither gate is a
 * security boundary; the permission matrix on the server is. These stop the
 * product showing somebody a console that will refuse them.
 */
"use client";

import * as React from "react";

import { AppShell } from "@/components/layout/app-shell";
import { RequireSection, SessionWarning } from "@/components/security";
import { Skeleton } from "@/components/ui/primitives";
import { RequireAuth } from "@/providers";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth fallback={<ShellSkeleton />}>
      {/* The shell still renders — the nav, the account menu, the way back —
          because somebody who followed a wrong link needs somewhere to go.
          What does not render is the section. */}
      <AppShell>
        <RequireSection>
          {/* Every list keeps its filters and page in the query string (UX-5),
              and a page reading `useSearchParams` needs a boundary above it
              or Next will not prerender the route. One here covers them all. */}
          <React.Suspense fallback={null}>{children}</React.Suspense>
        </RequireSection>
      </AppShell>
      {/* Outside the shell so it survives a page-level error boundary: a
          session about to end is exactly when somebody needs to be told. */}
      <SessionWarning />
    </RequireAuth>
  );
}

/** Mirrors the real shell's geometry so nothing jumps when it resolves. */
function ShellSkeleton() {
  return (
    <div className="min-h-dvh bg-bg">
      <div className="frame-top h-16" />
      <div className="mx-auto flex w-full max-w-[1600px]">
        <div className="frame-side frame-scope relative hidden w-64 shrink-0 p-3 lg:block">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="mb-1.5 h-9 w-full" />
          ))}
        </div>
        <div className="min-w-0 flex-1 space-y-4 px-4 py-6 sm:px-6 lg:px-8">
          <Skeleton className="h-7 w-56" />
          <Skeleton className="h-4 w-80" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <Skeleton className="h-64" />
        </div>
      </div>
    </div>
  );
}
