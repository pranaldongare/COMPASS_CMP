/**
 * What an erasure ticket asks its holder to do, item by item (2026-10-08).
 *
 * The office decides each appearance of the person in a collected asset -
 * erase, redact, retain until a date, or quarantine - and the ticket lists the
 * ones this holder holds, in the holder's words: which asset, and what to do
 * with it. The legal basis behind each decision stays with the office.
 */
import { Table, Td, Th, Tr } from "@/components/ui/primitives";
import { formatDate } from "@/lib/format";
import type { RightsScopeDecision } from "@/types";

/** The fields both sides have: the office's scope item and the holder's ticket item. */
export interface ListedItem {
  item_uuid: string;
  decision: RightsScopeDecision | null;
  retain_until: string | null;
  other_subjects: number;
  asset_type: string;
  source_asset_ref: string;
  source_name: string;
  project_name: string;
  collected_on: string;
}

/** What the holder does, in its words. */
export function whatToDo(item: ListedItem): string {
  switch (item.decision) {
    case "erase":
      return "Erase it";
    case "redact":
      return `Remove the person from it; keep the ${item.other_subjects === 1 ? "other person" : `other ${item.other_subjects} people`}`;
    case "retain":
      return item.retain_until ? `Keep it until ${formatDate(item.retain_until)}, then erase it` : "Keep it for now";
    case "quarantine":
      return "Set it aside, untouched, until the Privacy Office decides";
    default:
      return "Not decided yet";
  }
}

export function TicketItems({ items, title = "What to do with each item" }: { items: ListedItem[]; title?: string }) {
  const decided = items.filter((i) => i.decision);
  if (decided.length === 0) return null;
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold tracking-wide text-text-subtle uppercase">
        {title} · {decided.length}
      </h3>
      <Table>
        <caption className="sr-only">{title}</caption>
        <thead>
          <tr>
            <Th>Item</Th>
            <Th>Collected</Th>
            <Th>What to do</Th>
          </tr>
        </thead>
        <tbody>
          {decided.map((i) => (
            <Tr key={i.item_uuid}>
              <Td>
                <span className="font-mono text-xs">{i.source_asset_ref}</span>
                <span className="block text-xs text-text-muted">
                  {i.asset_type} · {i.source_name} · {i.project_name}
                </span>
              </Td>
              <Td className="whitespace-nowrap text-text-muted">{formatDate(i.collected_on)}</Td>
              <Td className="font-medium">{whatToDo(i)}</Td>
            </Tr>
          ))}
        </tbody>
      </Table>
    </section>
  );
}
