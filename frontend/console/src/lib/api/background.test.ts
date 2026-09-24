/**
 * A page polling itself is not somebody using it. The standing attention count
 * is always sent as background; a ticket list's first load is a person opening
 * the page and is not, its timed refreshes are.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { listMyTickets, requestsAttention } from "@/features/rights/api";
import { API, server } from "@/test/server";

function capture(path: string) {
  const seen: (string | null)[] = [];
  server.use(
    http.get(`${API}${path}`, ({ request }) => {
      seen.push(request.headers.get("X-CMP-Background"));
      return HttpResponse.json(path === "/requests/attention" ? { threads_unread: 0 } : []);
    }),
  );
  return seen;
}

describe("background requests", () => {
  it("marks the attention count as background", async () => {
    const seen = capture("/requests/attention");
    await requestsAttention();
    expect(seen).toEqual(["1"]);
  });

  it("marks a refresh, not a first load", async () => {
    const seen = capture("/tickets");
    await listMyTickets(false);
    await listMyTickets(true);
    expect(seen).toEqual([null, "1"]);
  });
});
