/**
 * How her requests refer to one another: a grievance to the request it
 * disputes, a re-run to the grievance that ordered it. Worked out from the
 * list she already has, so nothing is fetched twice.
 */
import type { MyRequest } from "@/types";

/** Which of her requests point at which: a grievance at the request it
 * disputes, a re-run at the grievance that ordered it. Computed from the list
 * she already has, so nothing is fetched twice. */
export function relate(requests: MyRequest[]): {
  byUuid: Map<string, MyRequest>;
  followers: Map<string, MyRequest[]>;
} {
  const byUuid = new Map(requests.map((r) => [r.request_uuid, r] as const));
  const followers = new Map<string, MyRequest[]>();
  for (const r of requests) {
    if (!r.linked_request_uuid || !byUuid.has(r.linked_request_uuid)) continue;
    followers.set(r.linked_request_uuid, [...(followers.get(r.linked_request_uuid) ?? []), r]);
  }
  return { byUuid, followers };
}

/** The first sentence or so of a response, for the card that refers to it. */
export function excerpt(text: string | null, limit = 220): string | null {
  if (!text) return null;
  const flat = text.replace(/\s+/g, " ").trim();
  if (flat.length <= limit) return flat;
  const cut = flat.slice(0, limit);
  return `${cut.slice(0, Math.max(cut.lastIndexOf(" "), limit - 40))}…`;
}

