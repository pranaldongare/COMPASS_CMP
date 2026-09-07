/**
 * The rights query layer against a fake network.
 *
 * Same discipline as the project tests: the real axios client, interceptors
 * and query wiring run; only the server is replaced. What these pin down is
 * that the register asks the right URL with its filters in the query string,
 * and that a 403 on the register surfaces as something the page can branch on without retrying.
 */

import { waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useRequest, useRequests } from "@/features/rights";
import { keys } from "@/lib/query";
import { makeRequestRow } from "@/test/fixtures";
import { API, HttpResponse, errorResponse, http, server } from "@/test/server";
import { renderHook } from "@/test/render";

describe("useRequests", () => {
  it("requests the register and unwraps the page", async () => {
    server.use(
      http.get(`${API}/requests`, () =>
        HttpResponse.json({ items: [makeRequestRow({ reference: "RR-2026-000007" })], next_cursor: null, total: 1 }),
      ),
    );
    const { result } = renderHook(() => useRequests());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0].reference).toBe("RR-2026-000007");
  });

  it("puts the filters in the query string", async () => {
    let seen: URL | null = null;
    server.use(
      http.get(`${API}/requests`, ({ request }) => {
        seen = new URL(request.url);
        return HttpResponse.json({ items: [], next_cursor: null, total: 0 });
      }),
    );
    const { result } = renderHook(() => useRequests({ status: "received", type: "erasure", overdue: true }));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(seen!.searchParams.get("status")).toBe("received");
    expect(seen!.searchParams.get("type")).toBe("erasure");
    expect(seen!.searchParams.get("overdue")).toBe("true");
  });

  it("surfaces a 403 without retrying", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/requests`, () => {
        calls += 1;
        return errorResponse("forbidden", "Your role does not permit this action", 403);
      }),
    );
    const { result } = renderHook(() => useRequests());
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.isForbidden).toBe(true);
    expect(calls).toBe(1);
  });
});

describe("useRequest", () => {
  it("does not fire without a uuid", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/requests/:uuid`, () => {
        calls += 1;
        return HttpResponse.json({});
      }),
    );
    renderHook(() => useRequest(undefined));
    await new Promise((r) => setTimeout(r, 20));
    expect(calls).toBe(0);
  });
});

describe("query keys", () => {
  it("hangs a request's trail off its own key", () => {
    const uuid = "99999999-9999-4999-8999-999999999999";
    const prefix = keys.rights.detail(uuid);
    expect(keys.rights.trail(uuid).slice(0, prefix.length)).toEqual([...prefix]);
  });

  it("keeps the register outside the per-request prefix", () => {
    expect(keys.rights.list()[0]).toBe("all");
  });
});
