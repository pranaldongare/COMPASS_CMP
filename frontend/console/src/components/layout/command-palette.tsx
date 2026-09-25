/**
 * The command palette: ⌘K (Ctrl+K elsewhere) from any page.
 *
 * Somebody who knows where they are going should not have to find it in a
 * sidebar of twenty links. The palette offers the same destinations the
 * sidebar does - read from `sectionsFor(me)`, so nothing appears here that the
 * server did not grant - plus the pages visited last and a few actions.
 *
 * Built on the Radix dialog like every other overlay here, for the focus trap,
 * Escape and focus return. Inside it the input is a combobox over a listbox,
 * with the highlighted option carried by `aria-activedescendant` so focus never
 * leaves the input while the arrow keys move.
 */
"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { CornerDownLeft, History, LogOut, Moon, Search, Sun } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";

import { labelFor, sectionsFor, type NavItem } from "@/components/layout/nav";
import { cn } from "@/lib/format";
import { useAuth, useTheme } from "@/providers";

interface Command {
  id: string;
  group: string;
  label: string;
  keywords?: string;
  icon: React.ComponentType<{ className?: string }>;
  run: () => void;
}

const RECENT_KEY = "cmp.console.recent";
const RECENT_MAX = 5;

/** The pages visited last, newest first. A convenience for this browser only:
 * storage can be missing or throw, and then there is simply no Recent group. */
export function readRecent(): string[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(parsed)
      ? parsed.filter((v): v is string => typeof v === "string")
      : [];
  } catch {
    return [];
  }
}

export function rememberVisit(href: string): void {
  try {
    const next = [href, ...readRecent().filter((h) => h !== href)].slice(0, RECENT_MAX);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // Private window or blocked storage: the palette works without history.
  }
}

/** Every word typed must appear somewhere in the command's words. */
function matches(command: Command, query: string): boolean {
  const haystack =
    `${command.label} ${command.group} ${command.keywords ?? ""}`.toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

/** Open and close on ⌘K / Ctrl+K from anywhere in the console. */
export function useCommandPaletteShortcut(toggle: () => void): void {
  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggle]);
}

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="overlay-in fixed inset-0 z-40 bg-black/40 backdrop-blur-[3px]" />
        <DialogPrimitive.Content
          className={cn(
            "palette-in fixed top-[12vh] left-1/2 z-50 w-[calc(100vw-2rem)] max-w-xl",
            "overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--shadow-pop)]",
          )}
        >
          <DialogPrimitive.Title className="sr-only">
            Search or jump to
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Type to filter pages and actions. Use the arrow keys to choose and Enter to
            open.
          </DialogPrimitive.Description>
          {/* Mounted only while open, so every opening starts from an empty
              query and the first option, with the history read afresh. */}
          {open && <PaletteBody close={() => onOpenChange(false)} />}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function PaletteBody({ close }: { close: () => void }) {
  const { me, signOut } = useAuth();
  const { resolved, setTheme } = useTheme();
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = React.useState("");
  const [active, setActive] = React.useState(0);
  const listId = React.useId();
  const listRef = React.useRef<HTMLDivElement>(null);
  const [recent] = React.useState(readRecent);

  const commands = React.useMemo(() => {
    const sections = sectionsFor(me);
    const go = (item: NavItem, group: string): Command => ({
      id: `${group}:${item.href}`,
      group,
      label: labelFor(item, me?.role),
      keywords: item.keywords,
      icon: item.icon,
      run: () => router.push(item.href),
    });

    const all = sections.flatMap((section) =>
      section.items.map((item) => go(item, section.title)),
    );
    const byHref = new Map(
      sections.flatMap((s) => s.items.map((i) => [i.href, i] as const)),
    );
    // The page you are on is not somewhere to go back to.
    const recents = recent
      .filter((href) => pathname !== href && !pathname.startsWith(`${href}/`))
      .map((href) => byHref.get(href))
      .filter((item): item is NavItem => Boolean(item))
      .map((item) => ({ ...go(item, "Recent"), icon: History }));

    const actions: Command[] = [
      {
        id: "action:theme",
        group: "Actions",
        label: `Switch to ${resolved === "dark" ? "light" : "dark"} theme`,
        keywords: "dark light mode appearance",
        icon: resolved === "dark" ? Sun : Moon,
        run: () => setTheme(resolved === "dark" ? "light" : "dark"),
      },
      {
        id: "action:sign-out",
        group: "Actions",
        label: "Sign out",
        keywords: "log out logout exit",
        icon: LogOut,
        run: signOut,
      },
    ];

    return { recents, all, actions };
  }, [me, pathname, recent, resolved, router, setTheme, signOut]);

  // Recent pages are a shortcut for the empty palette; once somebody types,
  // each page appears once, under its own section.
  const visible = query.trim()
    ? [...commands.all, ...commands.actions].filter((c) => matches(c, query))
    : [...commands.recents, ...commands.all, ...commands.actions];

  const groups: { title: string; commands: { command: Command; index: number }[] }[] = [];
  visible.forEach((command, index) => {
    const last = groups[groups.length - 1];
    if (last?.title === command.group) last.commands.push({ command, index });
    else groups.push({ title: command.group, commands: [{ command, index }] });
  });

  const current = Math.min(active, Math.max(visible.length - 1, 0));

  React.useEffect(() => {
    listRef.current
      ?.querySelector(`[data-index="${current}"]`)
      ?.scrollIntoView?.({ block: "nearest" });
  }, [current]);

  function run(command: Command | undefined) {
    if (!command) return;
    close();
    command.run();
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(visible.length ? (current + 1) % visible.length : 0);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(visible.length ? (current - 1 + visible.length) % visible.length : 0);
    } else if (event.key === "Home") {
      event.preventDefault();
      setActive(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActive(Math.max(visible.length - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      run(visible[current]);
    }
  }

  const optionId = (index: number) => `${listId}-option-${index}`;

  return (
    <>
      <div className="flex items-center gap-3 border-b border-border px-4">
        <Search className="size-4 shrink-0 text-text-subtle" aria-hidden="true" />
        <input
          autoFocus
          role="combobox"
          aria-expanded="true"
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={visible.length ? optionId(current) : undefined}
          aria-label="Search pages and actions"
          placeholder="Search pages and actions…"
          className="h-14 min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-text-subtle"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
        />
        <kbd className="hidden rounded-md border border-border bg-bg-inset px-1.5 py-0.5 text-2xs font-medium text-text-subtle sm:inline">
          Esc
        </kbd>
      </div>

      <div
        ref={listRef}
        id={listId}
        role="listbox"
        aria-label="Pages and actions"
        className="max-h-[min(60vh,26rem)] overflow-y-auto p-2"
      >
        {visible.length === 0 && (
          <p className="px-3 py-10 text-center text-sm text-text-muted">
            Nothing matches “{query.trim()}”.
          </p>
        )}
        {groups.map((group, g) => (
          <div
            key={group.title}
            role="group"
            aria-labelledby={`${listId}-group-${g}`}
            className="mb-1 last:mb-0"
          >
            <p
              id={`${listId}-group-${g}`}
              className="px-3 pt-2 pb-1 text-2xs font-semibold tracking-wider text-text-subtle uppercase"
            >
              {group.title}
            </p>
            {group.commands.map(({ command, index }) => {
              const selected = index === current;
              const Icon = command.icon;
              return (
                // The keyboard is the input's: with aria-activedescendant,
                // focus never lands on an option, so an option has no keys of
                // its own to listen for. The click is for the mouse.
                // eslint-disable-next-line jsx-a11y/click-events-have-key-events
                <div
                  key={command.id}
                  id={optionId(index)}
                  role="option"
                  aria-selected={selected}
                  data-index={index}
                  onMouseMove={() => setActive(index)}
                  onClick={() => run(command)}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm",
                    selected ? "bg-accent-subtle text-accent-text" : "text-text",
                  )}
                >
                  <Icon
                    className={cn(
                      "size-4 shrink-0",
                      selected ? "text-accent" : "text-text-subtle",
                    )}
                    aria-hidden="true"
                  />
                  <span className="min-w-0 flex-1 truncate">{command.label}</span>
                  {selected && (
                    <CornerDownLeft
                      className="size-3.5 shrink-0 text-accent"
                      aria-hidden="true"
                    />
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <div className="flex items-center gap-4 border-t border-border bg-bg-inset/60 px-4 py-2 text-2xs text-text-subtle">
        <span>
          <Key>↑</Key> <Key>↓</Key> to move
        </span>
        <span>
          <Key>↵</Key> to open
        </span>
        <span>
          <Key>Esc</Key> to close
        </span>
      </div>
    </>
  );
}

function Key({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded border border-border bg-surface px-1 font-sans text-2xs">
      {children}
    </kbd>
  );
}
