/**
 * The help manual page: a numbered table of contents, the sections in order,
 * and who to contact at the end.
 *
 * Laid out like a printed manual - one column to read, the contents beside it
 * on a desk and folded above it on a phone - because people read it start to
 * finish once and then come back to one section. So every section has an
 * anchor, the contents follow the reader down the page, and a search narrows
 * the manual to the sections that mention what was typed.
 *
 * Content is data (`HelpSection[]`); this renders whatever it is given.
 */
"use client";

import { AlertTriangle, ArrowUp, BookOpen, Info, Lightbulb, Search, X } from "lucide-react";
import * as React from "react";

import { Badge, EmptyState } from "@/components/ui/primitives";
import type { HelpBlock, HelpSection, RoleOption } from "@/features/help/types";
import { cn } from "@/lib/format";

/* ------------------------------------------------------------ inline text */

/** `[[Label]]` becomes a label chip; everything else is plain text. */
function Rich({ text }: { text: string }) {
  const parts = text.split(/\[\[(.+?)\]\]/g);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <span
            key={i}
            className="mx-0.5 inline-block rounded-md border border-border bg-bg-inset px-1.5 py-px text-[0.86em] font-medium whitespace-nowrap text-text"
          >
            {part}
          </span>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        ),
      )}
    </>
  );
}

/** Every word a section holds, for the search. */
function wordsOf(section: HelpSection): string {
  const blocks = section.blocks.flatMap((b) => {
    switch (b.kind) {
      case "p":
        return [b.text];
      case "note":
      case "tip":
      case "warning":
        return [b.title ?? "", b.text];
      case "steps":
      case "list":
        return [b.title ?? "", ...b.items];
      case "faq":
        return b.items.flatMap((i) => [i.q, i.a]);
      case "terms":
        return b.items.flatMap((i) => [i.term, i.meaning]);
    }
  });
  return [section.title, section.summary, ...blocks]
    .join(" ")
    .replace(/\[\[|\]\]/g, "")
    .toLowerCase();
}

/* ------------------------------------------------------------------ blocks */

const CALLOUT = {
  note: {
    icon: Info,
    className: "border-info-border bg-info-subtle text-info-text",
    label: "Note",
  },
  tip: {
    icon: Lightbulb,
    className: "border-success-border bg-success-subtle text-success-text",
    label: "Tip",
  },
  warning: {
    icon: AlertTriangle,
    className: "border-warning-border bg-warning-subtle text-warning-text",
    label: "Important",
  },
} as const;

function Block({ block }: { block: HelpBlock }) {
  switch (block.kind) {
    case "p":
      return (
        <p className="leading-relaxed text-text-muted">
          <Rich text={block.text} />
        </p>
      );
    case "steps":
      return (
        <div>
          {block.title && <h3 className="mb-3 text-base font-semibold">{block.title}</h3>}
          <ol className="space-y-3">
            {block.items.map((item, i) => (
              <li key={i} className="flex gap-3">
                <span
                  aria-hidden="true"
                  className="brand-gradient mt-0.5 grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold text-white shadow-[var(--shadow-sm)]"
                >
                  {i + 1}
                </span>
                <span className="leading-relaxed">
                  <span className="sr-only">Step {i + 1}: </span>
                  <Rich text={item} />
                </span>
              </li>
            ))}
          </ol>
        </div>
      );
    case "list":
      return (
        <div>
          {block.title && <h3 className="mb-2 text-base font-semibold">{block.title}</h3>}
          <ul className="space-y-2">
            {block.items.map((item, i) => (
              <li key={i} className="flex gap-3 leading-relaxed">
                <span
                  aria-hidden="true"
                  className="mt-2.5 size-1.5 shrink-0 rounded-full bg-accent"
                />
                <span>
                  <Rich text={item} />
                </span>
              </li>
            ))}
          </ul>
        </div>
      );
    case "note":
    case "tip":
    case "warning": {
      const c = CALLOUT[block.kind];
      const Icon = c.icon;
      return (
        <aside
          className={cn("flex gap-3 rounded-xl border px-4 py-3 text-sm", c.className)}
        >
          <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <div className="leading-relaxed">
            <p className="font-semibold">{block.title ?? c.label}</p>
            <p className="mt-0.5 text-text-muted">
              <Rich text={block.text} />
            </p>
          </div>
        </aside>
      );
    }
    case "faq":
      return (
        <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface">
          {block.items.map((item) => (
            <details
              key={item.q}
              className="group px-4 py-3 [&_summary::-webkit-details-marker]:hidden"
            >
              <summary className="flex cursor-pointer list-none items-start justify-between gap-3 font-medium">
                <span>
                  <Rich text={item.q} />
                </span>
                <span
                  aria-hidden="true"
                  className="mt-0.5 text-lg leading-none text-text-subtle transition-transform group-open:rotate-45"
                >
                  +
                </span>
              </summary>
              <p className="mt-2 leading-relaxed text-text-muted">
                <Rich text={item.a} />
              </p>
            </details>
          ))}
        </div>
      );
    case "terms":
      return (
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[minmax(9rem,auto)_1fr]">
          {block.items.map((item) => (
            <React.Fragment key={item.term}>
              <dt className="font-semibold">{item.term}</dt>
              <dd className="leading-relaxed text-text-muted">
                <Rich text={item.meaning} />
              </dd>
            </React.Fragment>
          ))}
        </dl>
      );
  }
}

/* ------------------------------------------------------------ scroll-spy */

/**
 * The section being read: the last one whose heading has scrolled up past
 * the sticky header. Measured on scroll rather than with an intersection
 * observer, which reports the section *ending* in view as well as the one
 * starting, and would highlight the one before.
 */
function useActiveSection(ids: string[]): string | null {
  const [active, setActive] = React.useState<string | null>(null);
  const key = ids.join("|");
  React.useEffect(() => {
    const list = key ? key.split("|") : [];
    let frame = 0;
    const measure = () => {
      frame = 0;
      let current: string | null = list[0] ?? null;
      for (const id of list) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= 120) current = id;
      }
      setActive(current);
    };
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(measure);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [key]);
  return active;
}

/** Shown once the reader is well down the page. */
function useScrolledPast(px: number): boolean {
  return React.useSyncExternalStore(
    (notify) => {
      window.addEventListener("scroll", notify, { passive: true });
      return () => window.removeEventListener("scroll", notify);
    },
    () => window.scrollY > px,
    () => false,
  );
}

/* -------------------------------------------------------------------- page */

export function HelpManual({
  product,
  intro,
  sections,
  roles,
  initialRole = "",
  contact,
}: {
  /** The product name for the heading, e.g. "COMPASS CMP". */
  product: string;
  intro: string;
  sections: HelpSection[];
  /** Offer a "sections for" filter over these roles. */
  roles?: RoleOption[];
  /** The role to filter to at first - the reader's own, when known. */
  initialRole?: string;
  /** The closing "contact us" panel. */
  contact: React.ReactNode;
}) {
  const [query, setQuery] = React.useState("");
  const [role, setRole] = React.useState(initialRole);
  // The reader's role can arrive after the first render (the session is asked
  // for); adopt it once, unless they have already chosen.
  const [seenInitial, setSeenInitial] = React.useState(initialRole);
  if (seenInitial !== initialRole) {
    setSeenInitial(initialRole);
    if (role === seenInitial) setRole(initialRole);
  }
  const searchRef = React.useRef<HTMLInputElement>(null);
  const searchId = React.useId();
  const roleId = React.useId();

  const numbered = sections.map((s, i) => ({
    section: s,
    number: i + 1,
    words: wordsOf(s),
  }));
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const shown = numbered.filter(
    ({ section, words: text }) =>
      (!role || !section.roles || section.roles.includes(role)) &&
      words.every((w) => text.includes(w)),
  );
  const active = useActiveSection(shown.map((s) => s.section.id));
  const past = useScrolledPast(900);
  const roleLabel = roles?.find((r) => r.value === role)?.label;

  const contents = (
    <ol className="space-y-0.5">
      {shown.map(({ section, number }) => (
        <li key={section.id}>
          <a
            href={`#${section.id}`}
            aria-current={active === section.id ? "location" : undefined}
            className={cn(
              "flex gap-2 rounded-lg px-2.5 py-1.5 text-sm transition-colors",
              active === section.id
                ? "bg-accent-subtle font-medium text-accent-text"
                : "text-text-muted hover:bg-bg-inset hover:text-text",
            )}
          >
            <span className="tabular w-5 shrink-0 text-right text-text-subtle">
              {number}
            </span>
            <span>{section.title}</span>
          </a>
        </li>
      ))}
    </ol>
  );

  return (
    <div className="relative">
      {/* ------------------------------------------------------------ hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div
          aria-hidden="true"
          className="aurora pointer-events-none absolute inset-0 -z-10"
        />
        <div className="mx-auto max-w-3xl px-4 pt-12 pb-10 text-center sm:pt-16">
          <p className="inline-flex items-center gap-1.5 rounded-full border border-accent-border/60 bg-accent-subtle px-3 py-1 text-2xs font-semibold tracking-wider text-accent-text uppercase">
            <BookOpen className="size-3.5" aria-hidden="true" />
            Help manual
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-5xl">
            {product} <span className="text-accent">Manual</span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl leading-relaxed text-text-muted">{intro}</p>

          <div className="mx-auto mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row">
            <div role="search" className="relative flex-1">
              <label htmlFor={searchId} className="sr-only">
                Search the manual
              </label>
              <Search
                className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-text-subtle"
                aria-hidden="true"
              />
              <input
                ref={searchRef}
                id={searchId}
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Escape" && query) {
                    e.preventDefault();
                    setQuery("");
                  }
                }}
                placeholder="Search the manual - e.g. withdraw, export, code"
                className={cn(
                  "h-12 w-full rounded-xl border border-border-strong bg-surface pr-10 pl-11 text-base shadow-[var(--shadow-sm)]",
                  "outline-none placeholder:text-text-subtle focus:border-accent focus:ring-2 focus:ring-[var(--accent-subtle)]",
                  "[&::-webkit-search-cancel-button]:hidden",
                )}
              />
              {query && (
                <button
                  type="button"
                  aria-label="Clear search"
                  onClick={() => {
                    setQuery("");
                    searchRef.current?.focus();
                  }}
                  className="absolute top-1/2 right-2.5 grid size-7 -translate-y-1/2 place-items-center rounded-md text-text-subtle hover:bg-bg-inset hover:text-text"
                >
                  <X className="size-4" aria-hidden="true" />
                </button>
              )}
            </div>
            {roles && (
              <div className="sm:w-56">
                <label htmlFor={roleId} className="sr-only">
                  Show sections for
                </label>
                <select
                  id={roleId}
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="h-12 w-full rounded-xl border border-border-strong bg-surface px-3 text-sm shadow-[var(--shadow-sm)] outline-none focus:border-accent focus:ring-2 focus:ring-[var(--accent-subtle)]"
                >
                  <option value="">Every role</option>
                  {roles.map((r) => (
                    <option key={r.value} value={r.value}>
                      For the {r.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <p className="mt-3 text-xs text-text-subtle" aria-live="polite">
            {shown.length === sections.length
              ? `${sections.length} sections`
              : `${shown.length} of ${sections.length} sections${roleLabel ? ` for the ${roleLabel}` : ""}${query ? ` mentioning “${query.trim()}”` : ""}`}
          </p>
        </div>
      </section>

      <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[16rem_minmax(0,1fr)] lg:py-12">
        {/* ------------------------------------------------ contents: desk */}
        <nav aria-label="Table of contents" className="hidden lg:block">
          <div className="sticky top-20 max-h-[calc(100dvh-6rem)] overflow-y-auto pr-1">
            <p className="mb-2 px-2.5 text-2xs font-semibold tracking-wider text-text-subtle uppercase">
              Table of contents
            </p>
            {contents}
          </div>
        </nav>

        <div className="min-w-0">
          {/* --------------------------------------------- contents: phone */}
          <details className="mb-6 rounded-xl border border-border bg-surface shadow-[var(--shadow-sm)] lg:hidden">
            <summary className="cursor-pointer px-4 py-3 text-sm font-semibold">
              Table of contents · {shown.length}
            </summary>
            <nav aria-label="Table of contents" className="border-t border-border p-2">
              {contents}
            </nav>
          </details>

          {shown.length === 0 && (
            <div className="rounded-2xl border border-border bg-surface">
              <EmptyState
                title="Nothing in the manual matches"
                description="Try a different word, or show every section."
                action={
                  <button
                    type="button"
                    onClick={() => {
                      setQuery("");
                      setRole("");
                    }}
                    className="rounded-lg border border-border-strong px-3 py-1.5 text-sm font-medium hover:bg-bg-inset"
                  >
                    Show every section
                  </button>
                }
              />
            </div>
          )}

          <div className="space-y-6">
            {shown.map(({ section, number }) => (
              <section
                key={section.id}
                id={section.id}
                aria-labelledby={`${section.id}-title`}
                className="scroll-mt-24 rounded-2xl border border-border bg-surface p-5 shadow-[var(--shadow-card)] sm:p-7"
              >
                <header className="mb-5 flex flex-wrap items-start gap-3">
                  <span
                    aria-hidden="true"
                    className="brand-gradient grid size-9 shrink-0 place-items-center rounded-xl text-sm font-semibold text-white shadow-[var(--shadow-sm)]"
                  >
                    {number}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h2
                      id={`${section.id}-title`}
                      className="text-xl font-semibold tracking-tight"
                    >
                      <span className="sr-only">{number}. </span>
                      <a href={`#${section.id}`} className="hover:underline">
                        {section.title}
                      </a>
                    </h2>
                    <p className="mt-1 text-sm text-text-muted">{section.summary}</p>
                  </div>
                  {section.roles && roles && (
                    <div className="flex flex-wrap gap-1.5">
                      {section.roles.map((r) => (
                        <Badge key={r} tone="neutral">
                          {roles.find((o) => o.value === r)?.label ?? r}
                        </Badge>
                      ))}
                    </div>
                  )}
                </header>
                <div className="space-y-5">
                  {section.blocks.map((block, i) => (
                    <Block key={i} block={block} />
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="mt-10">{contact}</div>
        </div>
      </div>

      {past && (
        <a
          href="#top"
          className="fixed right-4 bottom-4 z-30 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-sm font-medium shadow-[var(--shadow-pop)] hover:bg-bg-inset"
        >
          <ArrowUp className="size-4" aria-hidden="true" />
          Back to top
        </a>
      )}
    </div>
  );
}
