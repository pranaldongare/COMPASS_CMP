/**
 * A card that folds away.
 *
 * For the long reference parts of a page - the clock and path of a request, a
 * project's history - that somebody reads once and then wants out of the way.
 * The header is one button (`aria-expanded`, `aria-controls`); the body stays
 * mounted while folded, so nothing inside loses its state. With `storageKey`
 * the choice is remembered in this browser; storage that is missing or throws
 * just means it is not remembered.
 */
"use client";

import { ChevronDown } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/format";

const listeners = new Set<() => void>();
const memory = new Map<string, boolean>();

function read(key: string | undefined, fallback: boolean): boolean {
  if (!key) return fallback;
  try {
    const stored = localStorage.getItem(`cmp.collapse.${key}`);
    if (stored === "open") return true;
    if (stored === "closed") return false;
  } catch {
    // fall through to memory
  }
  return memory.get(key) ?? fallback;
}

function write(key: string, open: boolean): void {
  memory.set(key, open);
  try {
    localStorage.setItem(`cmp.collapse.${key}`, open ? "open" : "closed");
  } catch {
    // kept in memory for this page's life
  }
  listeners.forEach((notify) => notify());
}

/** Open or folded, remembered under `key` when one is given. */
export function useCollapsed(
  key: string | undefined,
  defaultOpen: boolean,
): [boolean, (open: boolean) => void] {
  const [local, setLocal] = React.useState(defaultOpen);
  const stored = React.useSyncExternalStore(
    (notify) => {
      listeners.add(notify);
      return () => listeners.delete(notify);
    },
    () => read(key, defaultOpen),
    () => defaultOpen,
  );
  if (!key) return [local, setLocal];
  return [stored, (open: boolean) => write(key, open)];
}

export function CollapsibleCard({
  title,
  description,
  icon: Icon,
  badge,
  actions,
  defaultOpen = true,
  storageKey,
  children,
  className,
}: {
  title: string;
  description?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  /** A count or status beside the title, visible while folded. */
  badge?: React.ReactNode;
  /** Controls in the header that are not the toggle. */
  actions?: React.ReactNode;
  defaultOpen?: boolean;
  /** Remember open or folded in this browser under this name. */
  storageKey?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useCollapsed(storageKey, defaultOpen);
  const bodyId = React.useId();

  return (
    <section
      className={cn(
        "overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--shadow-card)]",
        className,
      )}
    >
      <div className="flex items-start gap-3 px-5 py-4">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={() => setOpen(!open)}
          className="group -mx-1 flex min-w-0 flex-1 items-start gap-3 rounded-lg px-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]"
        >
          {Icon && (
            <Icon className="mt-0.5 size-4 shrink-0 text-text-subtle" aria-hidden="true" />
          )}
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-base font-semibold">{title}</span>
              {badge}
            </span>
            {description && (
              <span className="mt-1 block text-sm text-text-muted">{description}</span>
            )}
          </span>
          <ChevronDown
            aria-hidden="true"
            className={cn(
              "mt-0.5 size-5 shrink-0 text-text-subtle transition-transform duration-200 group-hover:text-text",
              open ? "rotate-180" : "rotate-0",
            )}
          />
        </button>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div id={bodyId} hidden={!open} className="border-t border-border">
        {children}
      </div>
    </section>
  );
}
