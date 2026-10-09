/**
 * The words of every message the platform sends.
 *
 * One card per junction, grouped by what the message is about: signing in,
 * consent, rights, staff. Each card is the editor for that message on each of
 * its channels. The list comes from the server and is complete by
 * construction: the code cannot send a message that is not a junction, so a
 * message added later appears here on the day it lands, with its variables
 * and its default words.
 *
 * Forty-odd editors in one column meant scrolling to find the one wanted
 * (2026-10-09). So the page opens on its categories, each with its count; a
 * search, a channel and "changed from the default" narrow it; and an index
 * beside the list jumps straight to a message. The filters live in the URL,
 * so a link can open the page on one category.
 *
 * Reachable by the administrator and the DPO. Everyone else receives these
 * words; these two roles choose them.
 */
"use client";

import { MessageSquareText } from "lucide-react";
import * as React from "react";

import {
  FilterBar,
  FilterSelect,
  SearchBox,
  useFilterParam,
} from "@/components/data-display/resource-list";
import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Skeleton,
} from "@/components/ui/primitives";
import { useMessages } from "@/features/messages";
import { MessageEditor } from "@/features/messages/components/message-editor";
import { cn } from "@/lib/format";
import type { MessageTemplate } from "@/types";

/** What each category holds, said once under its name. */
const ABOUT: Record<string, string> = {
  "Sign-in": "Codes and invitations that let somebody in.",
  Accounts: "Confirming and adding a person's contacts.",
  Consent: "Receipts for consent given and withdrawn.",
  Rights: "Rights requests, from acknowledgement to response, and the tickets to holders.",
  Breach: "Breach notices and the tickets and access that go with them.",
  Projects: "Approvals, sites and closure, to the staff who run a project.",
  Staff: "Changes to a staff member's own role, access and cover.",
};

const CHANNELS = [
  { value: "email", label: "Email" },
  { value: "sms", label: "SMS" },
];

const CHANGED = [
  { value: "changed", label: "Changed from the default" },
  { value: "default", label: "Default words" },
];

export default function MessagesPage() {
  return (
    <React.Suspense fallback={null}>
      <MessagesPageView />
    </React.Suspense>
  );
}

function MessagesPageView() {
  const messages = useMessages();
  const [q, setQ] = useFilterParam("q");
  const [group, setGroup] = useFilterParam("group");
  const [channel, setChannel] = useFilterParam("channel");
  const [changed, setChanged] = useFilterParam("changed");

  const all = React.useMemo(() => messages.data ?? [], [messages.data]);

  // Categories in the server's order, each counted over everything - the
  // count is where a category's messages are, not what the search left.
  const categories = React.useMemo(() => {
    const counts = new Map<string, number>();
    for (const m of all) counts.set(m.group, (counts.get(m.group) ?? 0) + 1);
    return [...counts].map(([name, count]) => ({ name, count }));
  }, [all]);

  const shown = React.useMemo(() => {
    const term = q.trim().toLowerCase();
    return all.filter((m) => {
      if (group && m.group !== group) return false;
      if (channel && !m.channels.some((c) => c.channel === channel)) return false;
      if (changed) {
        const isChanged = m.channels.some((c) => c.customised);
        if ((changed === "changed") !== isChanged) return false;
      }
      if (!term) return true;
      return [m.title, m.description, m.key, m.group].some((s) => s.toLowerCase().includes(term));
    });
  }, [all, q, group, channel, changed]);

  const groups = React.useMemo(() => {
    const order: string[] = [];
    const byGroup = new Map<string, MessageTemplate[]>();
    for (const m of shown) {
      if (!byGroup.has(m.group)) {
        order.push(m.group);
        byGroup.set(m.group, []);
      }
      byGroup.get(m.group)!.push(m);
    }
    return order.map((g) => ({ group: g, items: byGroup.get(g) ?? [] }));
  }, [shown]);

  const filtered = Boolean(q || group || channel || changed);
  const clear = () => {
    setQ("");
    setGroup("");
    setChannel("");
    setChanged("");
  };

  return (
    <>
      <PageHeader
        eyebrow="Oversight"
        title="Message templates"
        description="The words of every email and SMS the platform sends. Change them here; the default is what goes out until you do, and is one click away if you change your mind."
      />

      <Alert tone="info" className="mb-6">
        Placeholders such as <code className="font-mono">{"{code}"}</code> are filled in
        when a message is sent. Each message lists the ones it provides; a save that names
        any other is refused. Email and SMS are edited separately, because a phone screen is
        not an inbox.
      </Alert>

      {messages.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : messages.isError ? (
        <Alert tone="danger" title="Could not load the messages">
          {messages.error.userMessage()}
        </Alert>
      ) : (
        <>
          <nav aria-label="Message categories" className="mb-4 flex flex-wrap gap-2">
            <CategoryChip label="All" count={all.length} active={!group} onClick={() => setGroup("")} />
            {categories.map((c) => (
              <CategoryChip
                key={c.name}
                label={c.name}
                count={c.count}
                active={group === c.name}
                onClick={() => setGroup(group === c.name ? "" : c.name)}
              />
            ))}
          </nav>

          <FilterBar>
            <div className="w-72">
              <SearchBox
                label="Find a message"
                placeholder="Name, purpose or key"
                value={q}
                onSubmit={setQ}
              />
            </div>
            <FilterSelect
              label="Sent by"
              value={channel}
              onChange={setChannel}
              options={CHANNELS}
              allLabel="Email and SMS"
            />
            <FilterSelect
              label="Words"
              value={changed}
              onChange={setChanged}
              options={CHANGED}
              allLabel="Changed or not"
            />
            {filtered && (
              <Button variant="ghost" size="sm" onClick={clear}>
                Clear filters
              </Button>
            )}
          </FilterBar>

          <p className="mb-4 text-sm text-text-muted" aria-live="polite">
            {filtered
              ? `${shown.length} of ${all.length} messages`
              : `${all.length} messages in ${categories.length} categories`}
          </p>

          {shown.length === 0 ? (
            <Card>
              <CardBody className="text-sm text-text-muted">
                No message matches these filters.{" "}
                <button type="button" onClick={clear} className="text-accent-text hover:underline">
                  Show every message
                </button>
              </CardBody>
            </Card>
          ) : (
            <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
              {/* The index: every message the filters leave, one click away. */}
              <aside className="hidden lg:block">
                <nav
                  aria-label="Messages on this page"
                  className="sticky top-20 max-h-[calc(100vh-6rem)] space-y-4 overflow-y-auto pr-1"
                >
                  {groups.map(({ group: g, items }) => (
                    <div key={g}>
                      <a
                        href={`#group-${slug(g)}`}
                        className="text-xs font-semibold tracking-wide text-text-subtle uppercase hover:text-text"
                      >
                        {g}
                      </a>
                      <ul className="mt-1 space-y-0.5">
                        {items.map((m) => (
                          <li key={m.key}>
                            <a
                              href={`#message-${m.key}`}
                              className="block rounded-md px-2 py-1 text-sm text-text-muted hover:bg-surface-hover hover:text-text"
                            >
                              {m.title}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </nav>
              </aside>

              <div className="space-y-8">
                {groups.map(({ group: g, items }) => (
                  <section key={g} aria-labelledby={`group-${slug(g)}`}>
                    <h2
                      id={`group-${slug(g)}`}
                      className="flex scroll-mt-20 items-center gap-2 text-sm font-semibold tracking-wide text-text-muted uppercase"
                    >
                      <MessageSquareText className="size-4" aria-hidden="true" />
                      {g}
                      <span className="font-normal normal-case tabular">({items.length})</span>
                    </h2>
                    {ABOUT[g] && <p className="mt-1 mb-3 text-sm text-text-muted">{ABOUT[g]}</p>}
                    <div className={cn("space-y-4", !ABOUT[g] && "mt-3")}>
                      {items.map((m) => (
                        <Card key={m.key} id={`message-${m.key}`} className="scroll-mt-20">
                          <CardHeader>
                            <CardTitle>{m.title}</CardTitle>
                            <p className="mt-1 text-sm text-text-muted">{m.description}</p>
                          </CardHeader>
                          <CardBody>
                            <MessageEditor message={m} />
                          </CardBody>
                        </Card>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}

function CategoryChip({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors",
        active
          ? "border-accent bg-accent text-accent-contrast"
          : "border-border bg-surface text-text-muted hover:bg-surface-hover hover:text-text",
      )}
    >
      {label}
      <span className="tabular text-xs opacity-80">{count}</span>
    </button>
  );
}

/** "Sign-in" → "sign-in": an id that survives a category's spaces. */
function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
