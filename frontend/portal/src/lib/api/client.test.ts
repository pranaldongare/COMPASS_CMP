/**
 * The response interceptor: sealed values in any JSON body are opened before
 * a page sees them, in one call to this origin's `/dkms/decrypt`, and nothing
 * else about the response changes.
 *
 * Runs the real axios client against MSW at the network boundary, so what is
 * tested is the request the browser would send and the body a page would get -
 * not a mocked module agreeing with itself.
 */

import { afterEach, describe, expect, it } from "vitest";

import { apiGet, apiPost } from "@/lib/api/client";
import { API, HttpResponse, http, server } from "@/test/server";

// Real envelopes from the key service - the same three `deep.test.ts` uses.
const NAME = "SE::REsBAQNY0o7rJCgfEWj-d0FITi5nT2bKzXhQ3pOGL9Hk8w1YtmJY";
const EMAIL = "SE::REsBAjWbQ-khS5sacN5Z3yLHVxqQnm9AN9QrJLeV0up7eDkAnidmv-aSO8rH5XU_";
const TEXT = "SE::REsBCgS0cnTQzT85P3501uluS_bXRiQF1c8uF94TUKuGxiEq0MEpbf3SQcg5";

/** Answer `/dkms/decrypt` like the server route does, counting the calls. */
function decryptService(opened: Record<string, string>) {
  const calls: unknown[] = [];
  server.use(
    http.post("/dkms/decrypt", async ({ request }) => {
      const body = (await request.json()) as { data: Record<string, string>[] };
      calls.push(body);
      return HttpResponse.json({
        data: body.data.map((record) =>
          Object.fromEntries(
            Object.entries(record).map(([type, value]) => [type, opened[value] ?? value]),
          ),
        ),
      });
    }),
  );
  return calls;
}

describe("the response interceptor opens sealed values", () => {
  afterEach(() => server.resetHandlers());

  it("opens every sealed value in a page of rows, in one call, and leaves the rest", async () => {
    const calls = decryptService({
      [NAME]: "Amruta Shukla",
      [EMAIL]: "amruta@example.org",
      [TEXT]: "Please send my file.",
    });
    server.use(
      http.get(`${API}/users`, () =>
        HttpResponse.json({
          items: [
            { user_uuid: "u1", full_name: NAME, email: EMAIL, role: "dpo", is_minor: false },
            { user_uuid: "u2", full_name: "Plain Name", email: null, role: "dco", is_minor: null },
          ],
          total: 2,
          next_cursor: null,
          detail: { request_text: TEXT },
        }),
      ),
    );

    const body = await apiGet<{
      items: { user_uuid: string; full_name: string; email: string | null; role: string }[];
      total: number;
      detail: { request_text: string };
    }>("/users");

    expect(calls).toHaveLength(1);
    expect((calls[0] as { data: unknown[] }).data).toEqual([{ NAME }, { EMAIL }, { FREE_TEXT: TEXT }]);
    expect(body.items[0]).toMatchObject({
      user_uuid: "u1",
      full_name: "Amruta Shukla",
      email: "amruta@example.org",
      role: "dpo",
      is_minor: false,
    });
    expect(body.items[1]).toMatchObject({ full_name: "Plain Name", email: null, is_minor: null });
    expect(body.detail.request_text).toBe("Please send my file.");
    expect(body.total).toBe(2);
    expect(JSON.stringify(body)).not.toContain("SE::");
  });

  it("makes no decrypt call for a body with nothing sealed", async () => {
    const calls = decryptService({});
    server.use(
      http.get(`${API}/purposes`, () =>
        HttpResponse.json({ items: [{ name: "Gait research", status: "active" }], total: 1 }),
      ),
    );
    const body = await apiGet<{ items: { name: string }[] }>("/purposes");
    expect(calls).toHaveLength(0);
    expect(body.items[0]?.name).toBe("Gait research");
  });

  it("opens what a write returns, too", async () => {
    const calls = decryptService({ [NAME]: "Arjun Nominee", [EMAIL]: "arjun@example.org" });
    server.use(
      http.post(`${API}/me/nominations`, () =>
        HttpResponse.json(
          { nomination_uuid: "n1", nominee_name: NAME, nominee_email: EMAIL, status: "pending" },
          { status: 201 },
        ),
      ),
    );
    const body = await apiPost<{ nominee_name: string; nominee_email: string; status: string }>(
      "/me/nominations",
      { nominee_name: "Arjun Nominee", nominee_email: "arjun@example.org", rights: ["access"] },
    );
    expect(calls).toHaveLength(1);
    expect(body).toMatchObject({
      nominee_name: "Arjun Nominee",
      nominee_email: "arjun@example.org",
      status: "pending",
    });
  });

  it("leaves a value the service would not open as it arrived, never blank", async () => {
    decryptService({ [NAME]: "Amruta Shukla" }); // EMAIL comes back as it went
    server.use(
      http.get(`${API}/me`, () => HttpResponse.json({ full_name: NAME, email: EMAIL })),
    );
    const body = await apiGet<{ full_name: string; email: string }>("/me");
    expect(body.full_name).toBe("Amruta Shukla");
    expect(body.email).toBe(EMAIL);
  });

  it("never sends a sealed value anywhere but this origin's /dkms/decrypt", async () => {
    const elsewhere: string[] = [];
    server.use(
      http.post("/dkms/decrypt", async ({ request }) => {
        const body = (await request.json()) as { data: unknown[] };
        return HttpResponse.json({ data: body.data });
      }),
      http.post("*", ({ request }) => {
        elsewhere.push(request.url);
        return HttpResponse.json({});
      }),
      http.get(`${API}/me`, () => HttpResponse.json({ full_name: NAME })),
    );
    await apiGet("/me");
    expect(elsewhere.filter((url) => !url.includes("/dkms/decrypt"))).toEqual([]);
  });
});
