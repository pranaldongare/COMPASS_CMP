/**
 * The rights query layer against a fake network.
 *
 * The real axios client, interceptors and query wiring run; only the server is
 * replaced. What this pins down is that a data principal's requests come from
 * `/me`, and that the query keys are shaped so one invalidation reaches all of
 * a request's views.
 */

import { waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useMyRequests } from "@/features/rights";
import { keys } from "@/lib/query";
import { makeClock, makeMyRequest } from "@/test/fixtures";
import { API, HttpResponse, http, server } from "@/test/server";
import { renderHook } from "@/test/render";

describe("useMyRequests", () => {
  it("reads the principal's own requests from /me", async () => {
    server.use(http.get(`${API}/me/requests`, () => HttpResponse.json([makeMyRequest()])));
    const { result } = renderHook(() => useMyRequests());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0].clock.days_remaining).toBe(makeClock().days_remaining);
  });
});

describe("query keys", () => {
  it("hangs a request's trail off its own key", () => {
    const uuid = "99999999-9999-4999-8999-999999999999";
    const prefix = keys.me.request(uuid);
    expect(keys.me.requestTrail(uuid).slice(0, prefix.length)).toEqual([...prefix]);
  });
});
