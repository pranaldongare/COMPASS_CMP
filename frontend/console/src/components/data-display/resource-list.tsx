/**
 * Shared scaffolding for every list page.
 *
 * Fifteen list screens with hand-rolled pagination would drift into fifteen
 * subtly different behaviours - one resets the cursor on filter change, one
 * does not; one shows a spinner, one blanks the table. This holds the parts that
 * must behave identically:
 *
 * - **The cursor stack.** The API is cursor-paginated, so "page 3" does not
 *   exist. Keeping the stack of cursors is what gives users a Back button
 *   without inventing an offset the API would not honour.
 * - **Filter changes reset it.** A cursor describes a position in one particular
 *   result set; carrying it across a filter change asks for a page of a set that
 *   no longer exists.
 * - **Loading, empty, error and populated** are four distinct states, and each
 *   gets its own treatment. A table that renders empty while loading reads as
 *   "no results" and sends people looking for a bug that is not there.
 */
"use client";

import {
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  FolderKanban,
  Search,
  Shapes,
  SlidersHorizontal,
  UserRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";

import {
  Alert,
  Button,
  Card,
  EmptyState,
  Input,
  Table,
  TableSkeleton,
  Th,
} from "@/components/ui/primitives";
import type { ApiError } from "@/lib/errors";
import { cn } from "@/lib/format";
import type { Page } from "@/types";

/**
 * A list's state is its URL (review 2026-10-01, UX-5).
 *
 * Filters were read from the query string once and then kept in component
 * state, and the cursor stack never left it: reload, share the link, or open
 * a row and come Back, and the list was on page one with no filter. Now every
 * filter and the page live in the query string, written with the History API
 * (which Next keeps `useSearchParams` in step with), so the URL is the state.
 *
 * Written from `window.location` at the moment of the write, not from the
 * render's snapshot: a filter change and the page reset it implies are two
 * writes in one handler, and the second must not undo the first.
 */
const CURSOR = "cursor";
/** The cursors of the pages before this one, in order; "" is the first page. */
const PREVIOUS = "prev";

function writeUrl(change: (params: URLSearchParams) => void): void {
  const url = new URL(window.location.href);
  change(url.searchParams);
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

/** Re-render after a write, so the next read sees the URL it wrote. */
function useRerender(): () => void {
  const [, bump] = React.useReducer((n: number) => n + 1, 0);
  return bump;
}

/** Cursor stack, plus the reset that filter changes must trigger. In the URL. */
export function useCursorStack(): {
  cursor: string | undefined;
  canGoBack: boolean;
  /** 1 for the first page: how many pages back the cursor stack goes, plus one. */
  page: number;
  next: (cursor: string | null) => void;
  back: () => void;
  reset: () => void;
} {
  const params = useSearchParams();
  const rerender = useRerender();
  const cursor = params.get(CURSOR) ?? undefined;
  const previous = params.getAll(PREVIOUS);

  return {
    cursor,
    canGoBack: previous.length > 0,
    page: previous.length + 1,
    next: (c) => {
      writeUrl((p) => {
        p.append(PREVIOUS, p.get(CURSOR) ?? "");
        if (c) p.set(CURSOR, c);
        else p.delete(CURSOR);
      });
      rerender();
    },
    back: () => {
      writeUrl((p) => {
        const before = p.getAll(PREVIOUS);
        const last = before.pop();
        p.delete(PREVIOUS);
        for (const c of before) p.append(PREVIOUS, c);
        if (last) p.set(CURSOR, last);
        else p.delete(CURSOR);
      });
      rerender();
    },
    reset: () => {
      writeUrl(resetPage);
      rerender();
    },
  };
}

function resetPage(params: URLSearchParams): void {
  params.delete(CURSOR);
  params.delete(PREVIOUS);
}

export interface FilterOption {
  value: string;
  label: string;
}

/** A filter's icon, from its label (2026-10-10): the pills read as pictured
 *  choices without every page naming one. */
function filterIcon(label: string): LucideIcon {
  const l = label.toLowerCase();
  if (/role|owner|person|who|holder|by/.test(l)) return UserRound;
  if (/status|state|stage|clock|ticket/.test(l)) return CircleDot;
  if (/date|received|due|registered|from|to|when|month|period/.test(l)) return CalendarDays;
  if (/project/.test(l)) return FolderKanban;
  if (/processor|source|site|organisation/.test(l)) return Building2;
  if (/kind|type|category|purpose/.test(l)) return Shapes;
  return SlidersHorizontal;
}

/** The pill shape every filter shares (2026-10-10, the pill-chip style). */
function pillClass(set: boolean): string {
  return cn(
    "flex h-9 max-w-full items-center rounded-full border shadow-[var(--shadow-xs)] transition-colors",
    "focus-within:ring-3 focus-within:ring-[var(--accent-border)]/45",
    set ? "border-accent-border bg-accent-subtle" : "border-border bg-surface hover:border-border-strong",
  );
}

/** The small disc holding a filter's icon: blue once the filter is set. */
function IconDisc({ icon, set }: { icon: LucideIcon; set: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "grid size-6 shrink-0 place-items-center rounded-full transition-colors",
        set ? "bg-accent text-accent-contrast" : "bg-accent-subtle text-accent-text",
      )}
    >
      {React.createElement(icon, { className: "size-3.5" })}
    </span>
  );
}

export function FilterSelect({
  label,
  value,
  onChange,
  options,
  allLabel = "All",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: FilterOption[];
  /** The "everything" choice. `null` for a filter that always has a value -
   *  it then reads as set once it leaves its first option. */
  allLabel?: string | null;
}) {
  const id = React.useId();
  const set = allLabel === null ? value !== options[0]?.value : Boolean(value);
  // A pill (2026-10-10): an icon disc, the label, the value. A filter that is
  // set turns blue and gains an x, so what narrows the list is visible at a
  // glance and one click undoes it.
  const clearable = set && allLabel !== null;
  return (
    <div className={cn(pillClass(set), "pl-1.5")}>
      <label
        id={`${id}-label`}
        htmlFor={id}
        className="flex shrink-0 cursor-pointer items-center gap-2 pr-1 text-xs font-medium whitespace-nowrap text-text-subtle"
      >
        <IconDisc icon={filterIcon(label)} set={set} />
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "h-full max-w-48 min-w-0 cursor-pointer appearance-none truncate rounded-r-full bg-transparent pl-1 text-sm font-semibold outline-none",
          clearable ? "pr-1" : "select-chevron pr-9",
          set ? "text-accent-text" : "text-text",
        )}
      >
        {allLabel !== null && <option value="">{allLabel}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {clearable && (
        <button
          type="button"
          onClick={() => onChange("")}
          // Named apart from the field, so "Status" finds the select alone;
          // which filter it clears is its description.
          aria-label="Clear filter"
          aria-describedby={`${id}-label`}
          title={`Clear ${label}`}
          className="mr-1.5 grid size-6 shrink-0 place-items-center rounded-full text-accent-text transition-colors hover:bg-accent/15"
        >
          <X className="size-3.5" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

/** How long typing pauses before the list follows it. */
const SEARCH_DEBOUNCE_MS = 350;

/**
 * Search that follows the typing.
 *
 * The list updates once typing pauses, and at once on Enter; the × empties it.
 * `value` is the search in force - usually the URL's - and the box follows it
 * when it changes elsewhere, as when the filter's chip is cleared.
 *
 * `instant={false}` searches on Enter only: for a register searched by a whole
 * contact, where a fragment never matches and would only put pieces of
 * somebody's email into requests and logs.
 */
export function SearchBox({
  label = "Search",
  placeholder,
  onSubmit,
  value = "",
  instant = true,
}: {
  label?: string;
  placeholder?: string;
  onSubmit: (term: string) => void;
  value?: string;
  instant?: boolean;
}) {
  const id = React.useId();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [term, setTerm] = React.useState(value);
  // The last term handed to the list: a pause after typing back to it, or an
  // Enter on it, must not reset the list's pagination for nothing.
  const [sent, setSent] = React.useState(value);
  const submit = React.useRef(onSubmit);
  React.useEffect(() => {
    submit.current = onSubmit;
  });

  // The search in force changed without the box - a chip cleared, Back
  // pressed. Adjusted while rendering, as React recommends, rather than in an
  // effect that would paint the stale term first.
  const [seen, setSeen] = React.useState(value);
  if (seen !== value) {
    setSeen(value);
    setTerm(value);
    setSent(value);
  }

  const send = React.useCallback(
    (next: string) => {
      if (next === sent) return;
      setSent(next);
      submit.current(next);
    },
    [sent],
  );

  React.useEffect(() => {
    const next = term.trim();
    if (!instant || next === sent) return;
    const timer = window.setTimeout(() => send(next), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [term, send, instant, sent]);

  return (
    <form
      method="post"
      role="search"
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        send(term.trim());
      }}
    >
      <div className="w-64 max-w-full">
        {/* The magnifier and the placeholder say what it is; the label is for
            screen readers (2026-10-10). */}
        <label htmlFor={id} className="sr-only">
          {label}
        </label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-text-subtle"
            aria-hidden="true"
          />
          <Input
            ref={inputRef}
            id={id}
            type="search"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape" && term) {
                e.preventDefault();
                setTerm("");
                send("");
              }
            }}
            placeholder={placeholder ?? label}
            className="rounded-full pr-8 pl-9 [&::-webkit-search-cancel-button]:hidden"
          />
          {term && (
            <button
              type="button"
              aria-label="Clear search"
              title="Clear search"
              onClick={() => {
                setTerm("");
                send("");
                inputRef.current?.focus();
              }}
              className="absolute top-1/2 right-1.5 grid size-6 -translate-y-1/2 place-items-center rounded-full text-text-subtle transition-colors hover:bg-bg-inset hover:text-text"
            >
              <X className="size-3.5" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
      {/* Searching on Enter alone would be invisible; say so with a button. */}
      {!instant && (
        <Button type="submit" variant="secondary">
          Search
        </Button>
      )}
    </form>
  );
}

/**
 * The toolbar above a list.
 *
 * One row of compact controls over the table (2026-10-10; it was a boxed
 * panel with a label over every control, which pushed the data a third of the
 * way down the page). The table reads as the answer to the row above it.
 */
export function FilterBar({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2.5" role="group" aria-label="Filters">
      {children}
    </div>
  );
}

/**
 * A date filter in the same shape as `FilterSelect`: the label inside, blue
 * once set. `value` and `onChange` carry `YYYY-MM-DD`, as the browser's own
 * date field does.
 */
export function FilterDate({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
}) {
  const id = React.useId();
  return (
    <div className={cn(pillClass(Boolean(value)), "pl-1.5")}>
      <label
        htmlFor={id}
        className="flex shrink-0 items-center gap-2 pr-1 text-xs font-medium whitespace-nowrap text-text-subtle"
      >
        <IconDisc icon={CalendarDays} set={Boolean(value)} />
        {label}
      </label>
      <input
        id={id}
        type="date"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "h-full rounded-r-full bg-transparent pr-3 pl-1 text-sm font-semibold outline-none",
          value ? "text-accent-text" : "text-text-muted",
        )}
      />
    </div>
  );
}

/**
 * An on/off filter as a chip: "Nobody accountable". A real checkbox inside a
 * label, so it is announced and toggled as one.
 */
export function FilterToggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label
      className={cn(
        pillClass(checked),
        "cursor-pointer gap-2 px-3.5 text-sm font-medium whitespace-nowrap",
        checked ? "text-accent-text" : "text-text",
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-3.5 rounded border-border-strong accent-[var(--accent)]"
      />
      {label}
    </label>
  );
}

/**
 * Coming back to a list lands on the row you opened (UX review 2026-10-05).
 *
 * The URL already brings back the filter and the page; this brings back the
 * place in it. A click inside a row records that row's key for this exact
 * URL, in the tab's session storage; when the list next renders at that URL
 * with that row on it, the row is scrolled into view and its first link
 * focused - so a keyboard user returns to the row they left, not to the top.
 */
const RETURN_KEY = "cmp:list-return";

function useReturnToRow(
  keys: string[],
): [
  React.RefObject<HTMLTableSectionElement | null>,
  (event: React.MouseEvent, keys: string[]) => void,
] {
  const ref = React.useRef<HTMLTableSectionElement | null>(null);
  const joined = keys.join("|");

  React.useEffect(() => {
    if (!joined) return;
    let saved: { url: string; key: string } | null = null;
    try {
      saved = JSON.parse(window.sessionStorage.getItem(RETURN_KEY) ?? "null");
    } catch {
      return;
    }
    const here = `${window.location.pathname}${window.location.search}`;
    if (!saved || saved.url !== here || !joined.split("|").includes(saved.key)) return;
    // Rows are the body's direct children, in the order of the keys.
    const row = ref.current?.children[joined.split("|").indexOf(saved.key)];
    const target = row?.querySelector<HTMLElement>("a, button") ?? null;
    target?.scrollIntoView({ block: "center" });
    target?.focus({ preventScroll: true });
    window.sessionStorage.removeItem(RETURN_KEY);
  }, [joined]);

  const remember = (event: React.MouseEvent, rowKeys: string[]) => {
    const body = ref.current;
    const row = (event.target as HTMLElement).closest("tr");
    if (!body || !row || row.parentElement !== body) return;
    const key = rowKeys[Array.prototype.indexOf.call(body.children, row)];
    if (!key) return;
    try {
      window.sessionStorage.setItem(
        RETURN_KEY,
        JSON.stringify({ url: `${window.location.pathname}${window.location.search}`, key }),
      );
    } catch {
      // Storage refused (private mode, quota): the list still works, it just
      // will not return to the row.
    }
  };

  return [ref, remember];
}

/**
 * Renders the four states of a paginated list.
 *
 * `columns` and `row` stay with the caller: a shared component that also owned
 * the cells would need a column-definition mini-language, and those are always
 * harder to read than the JSX they replace.
 */
export function ResourceList<T>({
  query,
  columns,
  row,
  caption,
  empty,
  stack,
  keyOf,
  pageSize = 25,
}: {
  query: {
    data?: Page<T>;
    isLoading: boolean;
    isFetching: boolean;
    error: ApiError | null;
  };
  columns: string[];
  row: (item: T) => React.ReactNode;
  caption: string;
  empty: {
    title: string;
    description?: string;
    icon?: React.ReactNode;
    illustration?: React.ReactNode;
    action?: React.ReactNode;
  };
  stack: ReturnType<typeof useCursorStack>;
  keyOf: (item: T) => string;
  /** The `limit` the page asks for, to number the rows and pages. */
  pageSize?: number;
}) {
  const items = query.data?.items ?? [];
  const rowKeys = items.map(keyOf);
  const [bodyRef, rememberRow] = useReturnToRow(rowKeys);

  if (query.error) {
    return (
      <Alert tone="danger" title="Could not load this list">
        {query.error.isForbidden
          ? "You don't have access to this list. Go back to your dashboard, or ask your administrator if you need it."
          : query.error.userMessage()}
      </Alert>
    );
  }

  if (query.isLoading) {
    return (
      <Card>
        <TableSkeleton rows={6} cols={columns.length} />
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card>
        <EmptyState {...empty} />
      </Card>
    );
  }

  return (
    <>
      <Table>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((c, i) => (
              <Th key={c || `col-${i}`}>
                {/* A blank heading is the row-menu column: named for screen
                    readers, silent on screen. */}
                {c || <span className="sr-only">Actions</span>}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody ref={bodyRef} onClickCapture={(event) => rememberRow(event, rowKeys)}>
          {items.map((item) => (
            <React.Fragment key={keyOf(item)}>{row(item)}</React.Fragment>
          ))}
        </tbody>
      </Table>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="tabular text-xs text-text-subtle">
          {/* "Showing 26-50 of 312" (2026-10-10): where this page sits. */}
          Showing{" "}
          <span className="font-medium text-text-muted">
            {(stack.page - 1) * pageSize + 1}–{(stack.page - 1) * pageSize + items.length}
          </span>
          {query.data?.total != null && (
            <>
              {" "}of <span className="font-medium text-text-muted">{query.data.total}</span>
            </>
          )}
          {query.isFetching && (
            <span className="ml-2 inline-flex items-center gap-1.5 text-accent-text">
              <span
                className="size-1.5 animate-pulse rounded-full bg-accent"
                aria-hidden="true"
              />
              refreshing
            </span>
          )}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={!stack.canGoBack}
            onClick={stack.back}
          >
            <ChevronLeft aria-hidden="true" />
            Previous
          </Button>
          <span className="grid h-8 min-w-8 place-items-center rounded-md bg-accent px-2.5 text-xs font-semibold text-accent-contrast tabular">
            {stack.page}
          </span>
          {query.data?.total != null && query.data.total > pageSize && (
            <span className="self-center text-xs text-text-subtle tabular">
              of {Math.max(1, Math.ceil(query.data.total / pageSize))}
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            disabled={!query.data?.next_cursor}
            onClick={() => stack.next(query.data?.next_cursor ?? null)}
          >
            Next
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      </div>
    </>
  );
}

/**
 * A filter that lives in the URL.
 *
 * Dashboard figures link to the list that explains them — "3 pending approval"
 * goes to the projects list already filtered to pending approval — and the
 * filter stays in the URL as it changes, so a reload, a shared link or Back
 * from a row finds the same list. Changing it goes back to the first page: a
 * cursor describes a position in one result set, not in the next. An empty
 * value (or the fallback) is left out of the URL.
 *
 * `useSearchParams` forces client rendering, so any page calling this needs a
 * Suspense boundary above it or Next refuses to prerender the route.
 */
export function useFilterParam(
  name: string,
  fallback = "",
): [string, React.Dispatch<React.SetStateAction<string>>] {
  const params = useSearchParams();
  const rerender = useRerender();
  const value = params.get(name) ?? fallback;

  const setValue = React.useCallback<React.Dispatch<React.SetStateAction<string>>>(
    (next) => {
      writeUrl((p) => {
        const current = p.get(name) ?? fallback;
        const chosen = typeof next === "function" ? next(current) : next;
        if (chosen && chosen !== fallback) p.set(name, chosen);
        else p.delete(name);
        resetPage(p);
      });
      rerender();
    },
    [name, fallback, rerender],
  );
  return [value, setValue];
}
