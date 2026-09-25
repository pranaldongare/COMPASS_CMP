/**
 * Narrowing her own list of requests.
 *
 * Most people have one or two requests and see no controls at all. Past a
 * handful the list becomes something to search: which ones are still open,
 * and where is the one with that reference. Open means the server has not
 * closed it (`closed_at`), not a reading of the status here.
 *
 * Everything is filtered in the browser. The list is hers and already loaded;
 * a search that went to the server would put the words she typed into
 * requests and logs for nothing.
 */
"use client";

import { Search, X } from "lucide-react";
import * as React from "react";

import { Input } from "@/components/ui/primitives";
import { cn } from "@/lib/format";
import type { MyRequest } from "@/types";

/** Below this many requests the list is short enough to read whole. */
export const FILTER_FROM = 6;

export type RequestView = "open" | "closed" | "all";

const TYPE_WORDS: Record<MyRequest["request_type"], string> = {
  access: "access s.11",
  correction: "correction s.12",
  erasure: "erasure s.12",
  grievance: "grievance s.13",
};

function matches(request: MyRequest, query: string): boolean {
  const haystack = [
    request.reference,
    request.request_text,
    TYPE_WORDS[request.request_type],
    request.consent_project ?? "",
    request.linked_reference ?? "",
  ]
    .join(" ")
    .toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

export function useRequestFilter(requests: MyRequest[]) {
  const [view, setView] = React.useState<RequestView>("all");
  const [query, setQuery] = React.useState("");

  const counts = {
    open: requests.filter((r) => !r.closed_at).length,
    closed: requests.filter((r) => r.closed_at).length,
    all: requests.length,
  };
  const shown = requests.filter(
    (r) =>
      (view === "all" || (view === "open" ? !r.closed_at : Boolean(r.closed_at))) &&
      matches(r, query),
  );

  return {
    view,
    setView,
    query,
    setQuery,
    counts,
    shown,
    /** Show everything again - so a jump to a card the filter hid lands on it. */
    reset: () => {
      setView("all");
      setQuery("");
    },
    isShown: (uuid: string) => shown.some((r) => r.request_uuid === uuid),
  };
}

const VIEWS: { value: RequestView; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
];

export function RequestFilter({ filter }: { filter: ReturnType<typeof useRequestFilter> }) {
  const name = React.useId();
  const searchId = React.useId();
  const inputRef = React.useRef<HTMLInputElement>(null);

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      {/* Native radios, so the arrow keys and the screen reader's "1 of 3"
          come from the browser; the pills are only their clothes. */}
      <fieldset className="inline-flex rounded-xl border border-border bg-bg-inset/70 p-1">
        <legend className="sr-only">Show requests</legend>
        {VIEWS.map((v) => {
          const checked = filter.view === v.value;
          return (
            <label
              key={v.value}
              className={cn(
                "relative flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
                "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[var(--accent-subtle)]",
                checked
                  ? "bg-surface font-medium text-text shadow-[var(--shadow-sm)]"
                  : "text-text-muted hover:text-text",
              )}
            >
              <input
                type="radio"
                name={name}
                value={v.value}
                checked={checked}
                onChange={() => filter.setView(v.value)}
                className="sr-only"
              />
              {v.label}
              <span
                className={cn(
                  "tabular rounded-full px-1.5 text-2xs",
                  checked
                    ? "bg-accent-subtle text-accent-text"
                    : "bg-surface/70 text-text-subtle",
                )}
              >
                {filter.counts[v.value]}
              </span>
            </label>
          );
        })}
      </fieldset>

      <div role="search" className="relative w-full sm:w-72">
        <label htmlFor={searchId} className="sr-only">
          Search your requests
        </label>
        <Search
          className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-text-subtle"
          aria-hidden="true"
        />
        <Input
          ref={inputRef}
          id={searchId}
          type="search"
          value={filter.query}
          onChange={(e) => filter.setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape" && filter.query) {
              e.preventDefault();
              filter.setQuery("");
            }
          }}
          placeholder="Reference, kind or words"
          className="pr-8 pl-8 [&::-webkit-search-cancel-button]:hidden"
        />
        {filter.query && (
          <button
            type="button"
            aria-label="Clear search"
            title="Clear search"
            onClick={() => {
              filter.setQuery("");
              inputRef.current?.focus();
            }}
            className="absolute top-1/2 right-1.5 grid size-6 -translate-y-1/2 place-items-center rounded-md text-text-subtle transition-colors hover:bg-bg-inset hover:text-text"
          >
            <X className="size-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
