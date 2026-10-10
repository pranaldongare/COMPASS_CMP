/**
 * What a route shows while it loads and when it fails (2026-10-10).
 *
 * Used by `error.tsx`, `global-error.tsx` and `loading.tsx`. Before these, a
 * crash in a page showed the framework's bare error screen. The failure panel
 * says something went wrong, offers to try again and the way home, and shows
 * the error's digest - the reference the server logged it under - never the
 * message or stack, which can carry data.
 */
"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { Button, Skeleton } from "@/components/ui/primitives";

export function RouteError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  React.useEffect(() => {
    // An error tracker hooks in here in a deployment; the console in development.
    console.error("Route error", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6 py-12">
      <div className="animate-in max-w-md text-center">
        <span className="mx-auto grid size-12 place-items-center rounded-full bg-warning-subtle text-warning-text">
          <AlertTriangle className="size-6" aria-hidden="true" />
        </span>
        <h1 className="mt-4 text-xl font-semibold">Something went wrong</h1>
        <p className="mt-2 text-sm text-text-muted">
          This page could not be shown. Nothing you entered has been lost by trying again.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button variant="primary" onClick={() => retry()}>
            <RotateCcw aria-hidden="true" />
            Try again
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/">Go home</Link>
          </Button>
        </div>
        {error.digest && (
          <p className="mt-6 text-xs text-text-subtle">
            Reference <span className="font-mono">{error.digest}</span>
          </p>
        )}
      </div>
    </div>
  );
}

/** A page-shaped placeholder: a title, a toolbar and a table. */
export function RouteLoading() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-9 w-44" />
        <Skeleton className="h-9 w-44" />
      </div>
      <div className="space-y-px overflow-hidden rounded-lg border border-border bg-bg-subtle">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex gap-4 px-4 py-4">
            <Skeleton className="h-4 w-1/4" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-4 w-24" />
          </div>
        ))}
      </div>
    </div>
  );
}
