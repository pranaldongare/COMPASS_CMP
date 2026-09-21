/**
 * The shape of the rows a filter selects, before the rows themselves.
 *
 * Four numbers and four single-series bar lists: how many entries, over what
 * span, by area, by event, by the actor's role, and per day for the last
 * thirty. One hue throughout, because every bar is the same measure (a
 * count) and colour would otherwise suggest a difference that is not there;
 * every bar carries its label and its number in text, so nothing is read
 * from colour alone, and the whole strip is a table a screen reader walks.
 *
 * The numbers are computed by the server over exactly the rows the list
 * shows - same filters, same query - so they never disagree with the page.
 */
"use client";

import { Card, CardBody, Skeleton } from "@/components/ui/primitives";
import { formatDate, humanise } from "@/lib/format";
import type { AuditSummary, AuditVocabulary } from "@/types";

function Bars({
  title,
  rows,
  labelOf,
}: {
  title: string;
  rows: { key: string; count: number }[];
  labelOf: (key: string) => string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <div>
      <h3 className="mb-2 text-2xs font-semibold tracking-wider text-text-subtle uppercase">
        {title}
      </h3>
      {rows.length === 0 ? (
        <p className="text-sm text-text-subtle">Nothing yet.</p>
      ) : (
        <table className="w-full text-sm">
          <caption className="sr-only">{title}</caption>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <th
                  scope="row"
                  className="w-1/2 truncate py-0.5 pr-2 text-left font-normal text-text"
                >
                  {labelOf(r.key)}
                </th>
                <td className="py-0.5">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 rounded-r-sm bg-accent"
                      style={{ width: `${Math.max(2, (r.count / max) * 100)}%` }}
                      title={`${labelOf(r.key)}: ${r.count}`}
                      aria-hidden="true"
                    />
                    <span className="text-text-muted tabular-nums">{r.count}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Daily({ rows, days }: { rows: { day: string; count: number }[]; days: number }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  const total = rows.reduce((n, r) => n + r.count, 0);
  return (
    <div>
      <h3 className="mb-2 text-2xs font-semibold tracking-wider text-text-subtle uppercase">
        Last {days} days · {total} entries
      </h3>
      {rows.length === 0 ? (
        <p className="text-sm text-text-subtle">Nothing in this period.</p>
      ) : (
        <>
          <div
            className="flex h-16 items-end gap-px"
            role="img"
            aria-label={`Entries per day, last ${days} days`}
          >
            {rows.map((r) => (
              <div
                key={r.day}
                className="min-w-1 flex-1 rounded-t-sm bg-accent"
                style={{ height: `${Math.max(4, (r.count / max) * 100)}%` }}
                title={`${formatDate(r.day)}: ${r.count}`}
              />
            ))}
          </div>
          <table className="sr-only">
            <caption>Entries per day</caption>
            <tbody>
              {rows.map((r) => (
                <tr key={r.day}>
                  <th scope="row">{formatDate(r.day)}</th>
                  <td>{r.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 flex justify-between text-xs text-text-subtle">
            <span>{formatDate(rows[0].day)}</span>
            <span>{formatDate(rows[rows.length - 1].day)}</span>
          </p>
        </>
      )}
    </div>
  );
}

export function AuditSummaryStrip({
  summary,
  vocabulary,
  isLoading,
}: {
  summary: AuditSummary | undefined;
  vocabulary: AuditVocabulary | undefined;
  isLoading: boolean;
}) {
  if (isLoading || !summary) {
    return <Skeleton className="mb-4 h-40" />;
  }
  const groupLabel = (g: string) =>
    vocabulary?.event_groups.find((x) => x.value === g)?.label ?? humanise(g);
  const eventLabel = (e: string) => {
    const known = vocabulary?.event_types.find((x) => x.value === e);
    return known ? `${known.group_label}: ${known.label}` : humanise(e.replace(/\./g, " "));
  };
  const top = summary.by_event[0];

  return (
    <Card className="mb-4">
      <CardBody>
        <dl className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <dt className="text-xs text-text-subtle">Entries</dt>
            <dd className="text-xl font-semibold tabular-nums">
              {summary.total.toLocaleString()}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-subtle">Span</dt>
            <dd className="text-sm">
              {summary.first_at && summary.last_at
                ? `${formatDate(summary.first_at)} to ${formatDate(summary.last_at)}`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-subtle">Most common event</dt>
            <dd className="truncate text-sm" title={top ? eventLabel(top.key) : undefined}>
              {top ? `${eventLabel(top.key)} (${top.count})` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-subtle">Areas touched</dt>
            <dd className="text-xl font-semibold tabular-nums">
              {summary.by_group.length}
            </dd>
          </div>
        </dl>

        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          <Bars title="By area" rows={summary.by_group} labelOf={groupLabel} />
          <Bars
            title="Top events"
            rows={summary.by_event.slice(0, 8)}
            labelOf={(e) => eventLabel(e)}
          />
          <Bars title="By actor role" rows={summary.by_actor_role} labelOf={humanise} />
          <Daily rows={summary.by_day} days={summary.days} />
        </div>
      </CardBody>
    </Card>
  );
}
