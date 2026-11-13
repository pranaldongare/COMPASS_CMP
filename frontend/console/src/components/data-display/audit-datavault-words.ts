/**
 * What the trail says of DataVault, in words (0070).
 *
 * Two events: a rights request checked in DataVault - by the office's press,
 * or by the platform as holders were found - and the administrator's change
 * to where DataVault is reached. Each sentence is built from what its row
 * carries and no more. The row holds counts and a short code for a failure,
 * never an asset, a path, the address or the key, so neither does a sentence.
 */
import type { AuditEntry } from "@/types";

type Detail = Record<string, unknown>;

/** Why a check was not answered, by the code the row keeps. */
const NOT_ANSWERED: Record<string, string> = {
  timeout: "DataVault did not answer in time",
  unreachable: "DataVault could not be reached",
  unreadable: "DataVault answered, but not in the agreed format",
  too_many: "DataVault listed more assets than are read in one answer",
  status_401: "DataVault refused the key",
  status_403: "DataVault refused the key",
  status_404: "DataVault does not know this address, or this person",
};

function notAnswered(code: unknown): string {
  if (typeof code !== "string") return "the check did not complete";
  if (NOT_ANSWERED[code]) return NOT_ANSWERED[code];
  return code.startsWith("status_")
    ? `DataVault answered with an error (${code.slice("status_".length)})`
    : "the check did not complete";
}

const num = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const WORDS: Record<string, (d: Detail) => string> = {
  "datavault.checked": (d) => {
    const asked = d.automatic
      ? "The platform asked DataVault what it holds of the person, as holders were found"
      : "DataVault was asked what it holds of the person";
    if (d.outcome === "failed")
      return `${asked}. It was not answered: ${notAnswered(d.failure)}.`;
    const assets = num(d.assets);
    if (assets === null) return `${asked}.`;
    if (assets === 0) return `${asked}. It holds nothing.`;
    const unmatched = num(d.unmatched);
    return (
      `${asked}. It listed ${assets} ${assets === 1 ? "asset" : "assets"}` +
      `${unmatched ? `, ${unmatched} not matched to this person's records` : ""}.`
    );
  },
  "datavault.connection_changed": (d) => {
    const changed = [
      d.address_changed ? "the address" : null,
      d.key_changed ? (d.key_set ? "the key" : "the key, which was removed") : null,
      d.header_changed ? "the header the key is sent in" : null,
    ].filter(Boolean);
    const said = changed.length
      ? `The DataVault connection was changed: ${changed.join(", ")}.`
      : "The DataVault connection was saved.";
    if (d.enabled === d.was_enabled) return said;
    return `${said} It was switched ${d.enabled ? "on" : "off"}.`;
  },
};

/** The sentence for a DataVault event, or null for any other. */
export function datavaultSentence(entry: AuditEntry): string | null {
  const words = WORDS[entry.event_type];
  return words ? words((entry.detail ?? {}) as Detail) : null;
}
