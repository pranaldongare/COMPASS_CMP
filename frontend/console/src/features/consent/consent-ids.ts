/**
 * Consent IDs out of whatever somebody pastes or uploads (2026-10-15).
 *
 * A list arrives from an auditor or a downstream store: one ID a line, a
 * comma-separated run, or a CSV. A CSV with a `consent_uuid` column - the
 * archive's own manifest is one - is read by that column alone, because the
 * same rows carry the principal's and the project's IDs as well, and those
 * are not consent IDs.
 */

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;

export interface ParsedIds {
  /** Distinct, lower-case, in the order first seen. */
  ids: string[];
  /** How many repeated an ID already in the list. */
  repeats: number;
  /** Non-empty lines with no ID in them, for the person to check. */
  unread: string[];
}

function columnOf(text: string): string[] | null {
  const [head, ...rows] = text.split(/\r?\n/);
  const columns = head.split(",").map((c) => c.trim().replace(/^"|"$/g, "").toLowerCase());
  const at = columns.indexOf("consent_uuid");
  if (at < 0) return null;
  return rows.map((row) => (row.split(",")[at] ?? "").trim().replace(/^"|"$/g, ""));
}

export function consentIdsIn(text: string): ParsedIds {
  const cells = columnOf(text) ?? text.split(/\r?\n/);
  const seen = new Set<string>();
  let repeats = 0;
  const unread: string[] = [];
  for (const cell of cells) {
    const found = cell.match(UUID) ?? [];
    if (found.length === 0 && cell.trim()) unread.push(cell.trim());
    for (const id of found.map((f) => f.toLowerCase())) {
      if (seen.has(id)) repeats += 1;
      else seen.add(id);
    }
  }
  return { ids: [...seen], repeats, unread };
}
