/**
 * What the trail says of DataVault, in words (0070, 0071).
 *
 * A rights request checked in DataVault - by the office's press, or by the
 * platform as holders were found; the administrator's change to where
 * DataVault is reached; on an erasure request, DataVault told to erase and
 * asked how far it has got; and a consent change queued for DataVault and
 * delivered to it. Each sentence is built from what its row carries and no
 * more. The row holds counts, purpose codes and a short code for a failure,
 * never an asset, a path, a reason DataVault gave, the address or the key, so
 * neither does a sentence.
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

function notAnswered(code: unknown, otherwise = "the check did not complete"): string {
  if (typeof code !== "string") return otherwise;
  if (code === "status_400") return "DataVault refused it as badly formed";
  if (code === "status_409")
    return "DataVault has this instruction with a different list of assets";
  if (code === "status_404") return "DataVault does not know this address";
  if (NOT_ANSWERED[code]) return NOT_ANSWERED[code];
  return code.startsWith("status_")
    ? `DataVault answered with an error (${code.slice("status_".length)})`
    : otherwise;
}

const num = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const assets = (n: number) => `${n} ${n === 1 ? "asset" : "assets"}`;

/** "2 erased, 1 pending": the statuses an answer counted, in that order. */
function counted(d: Detail): string {
  return (
    [
      ["erased", "erased"],
      ["pending", "pending"],
      ["failed", "not erased"],
      ["not_held", "not held"],
    ] as const
  )
    .map(([key, words]) => [num(d[key]) ?? 0, words] as const)
    .filter(([n]) => n > 0)
    .map(([n, words]) => `${n} ${words}`)
    .join(", ");
}

/** What happened to a consent, as a message to DataVault names it. */
const CHANGE: Record<string, string> = {
  withdrawn: "the consent was withdrawn",
  partly_withdrawn: "part of the consent was withdrawn",
  expired: "the validity of a purpose ran out",
  granted_again: "purposes were granted again",
};

const codes = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];

function changeSaid(d: Detail): string {
  const what = CHANGE[String(d.change)] ?? "the consent changed";
  const sequence = num(d.sequence);
  return `${sequence !== null ? ` (message ${sequence})` : ""}: ${what}`;
}

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
    const also = [
      d.erasure_address_changed ? "The erasure address was changed." : null,
      typeof d.id_format === "string" && d.id_format_was && d.id_format !== d.id_format_was
        ? `IDs are now sent as ${d.id_format === "uuid" ? "UUIDs" : "numeric IDs"}.`
        : null,
      typeof d.consent_changes === "boolean" && d.consent_changes !== d.consent_changes_were
        ? `Consent changes were switched ${d.consent_changes ? "on" : "off"}.`
        : null,
    ].filter(Boolean);
    const switched =
      d.enabled === d.was_enabled ? "" : ` It was switched ${d.enabled ? "on" : "off"}.`;
    return [said + switched, ...also].join(" ");
  },
  "datavault.erasure_sent": (d) => {
    const n = num(d.assets);
    const sent =
      n === null
        ? "DataVault was told to erase this request's assets"
        : `DataVault was told to erase ${assets(n)}`;
    const instructions = num(d.instructions);
    const parts =
      instructions && instructions > 1 ? `, in ${instructions} instructions` : "";
    const left = num(d.left_out);
    const leftOut = left
      ? ` ${assets(left)} DataVault listed ${left === 1 ? "was" : "were"} left out: the request is about one consent.`
      : "";
    return `${sent}${parts}.${leftOut}`;
  },
  "datavault.erasure_checked": (d) => {
    const asked = d.again
      ? "DataVault was asked how far the erasure has got"
      : "DataVault was sent the instruction to erase";
    if (d.outcome === "failed")
      return `${asked}. It was not answered: ${notAnswered(d.failure, "the instruction was not answered")}.`;
    const line = counted(d);
    return line
      ? `${asked}. It answered: ${line}.`
      : `${asked}. It answered nothing of them.`;
  },
  "datavault.consent_change_queued": (d) => {
    const granted = codes(d.purposes_granted);
    const removed = codes(d.purposes_removed);
    const use =
      d.action === "lift_restriction"
        ? `The assets may be used again for ${granted.join(", ") || "no purpose"}.`
        : granted.length
          ? `The assets are to be used only for ${granted.join(", ")}.`
          : "The assets are not to be used at all.";
    const gone = removed.length ? ` Taken away: ${removed.join(", ")}.` : "";
    return `To tell DataVault${changeSaid(d)}. ${use}${gone}`;
  },
  "datavault.consent_change_delivered": (d) => {
    const n = num(d.assets_affected);
    const outcome =
      d.result === "duplicate"
        ? "It had the message already."
        : d.result === "stale"
          ? "It had a later message for this consent already, and changed nothing."
          : n === null
            ? "It applied it."
            : n === 0
              ? "It applied it; it holds no asset under this consent."
              : `It applied it to ${assets(n)}.`;
    return `DataVault was told${changeSaid(d)}. ${outcome}`;
  },
};

/** The sentence for a DataVault event, or null for any other. */
export function datavaultSentence(entry: AuditEntry): string | null {
  const words = WORDS[entry.event_type];
  return words ? words((entry.detail ?? {}) as Detail) : null;
}
