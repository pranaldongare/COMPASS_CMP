/**
 * The response walker: finds every sealed value wherever it sits, opens them
 * all in one call, and puts each back where it came from.
 *
 * The envelopes below are real ones, produced by the key service, so `typeOf`
 * is tested against the bytes it will actually meet and not against a guess at
 * the format.
 */

import { describe, expect, it, vi } from "vitest";

import { decryptDeep, hasSealed, typeOf } from "@/lib/dkms/deep";

// Produced by POST /bulk_encrypt with {"n": NAME, "e": EMAIL, "t": FREE_TEXT}.
const NAME = "SE::REsBAQNY0o7rJCgfEWj-d0FITi5nT2bKzXhQ3pOGL9Hk8w1YtmJY";
const EMAIL = "SE::REsBAjWbQ-khS5sacN5Z3yLHVxqQnm9AN9QrJLeV0up7eDkAnidmv-aSO8rH5XU_";
const TEXT = "SE::REsBCgS0cnTQzT85P3501uluS_bXRiQF1c8uF94TUKuGxiEq0MEpbf3SQcg5";

describe("typeOf", () => {
  it("reads the type off the envelope header", () => {
    expect(typeOf(NAME)).toBe("NAME");
    expect(typeOf(EMAIL)).toBe("EMAIL");
    expect(typeOf(TEXT)).toBe("FREE_TEXT");
  });

  it("answers null for anything that is not one of ours", () => {
    expect(typeOf("Amruta Shukla")).toBeNull();
    expect(typeOf("SE::")).toBeNull();
    expect(typeOf("SE::!!!!not-base64")).toBeNull();
    expect(typeOf("SE::QUJDRA==")).toBeNull(); // valid base64, wrong magic
  });
});

describe("hasSealed", () => {
  it("is false for a body with nothing sealed, however deep", () => {
    expect(hasSealed({ items: [{ a: { b: ["plain", 1, null] } }], total: 3 })).toBe(false);
  });
  it("is true for one sealed string three levels down", () => {
    expect(hasSealed({ items: [{ owner: { full_name: NAME } }] })).toBe(true);
  });
});

describe("decryptDeep", () => {
  it("opens every sealed value in one request and puts each back in place", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        data: [
          { NAME: "Amruta Shukla" },
          { FREE_TEXT: "Please send my file." },
          { EMAIL: "a@x.org" },
        ],
      }),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    const body = {
      items: [
        { id: "1", created_by_name: NAME, nested: { request_text: TEXT } },
        { id: "2", contact: EMAIL, count: 4, when: null },
      ],
      total: 2,
    };

    const out = await decryptDeep(body);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const sent = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(sent.data).toEqual([{ NAME }, { FREE_TEXT: TEXT }, { EMAIL }]);
    expect(sent.key).toEqual({ NAME: "NAME", FREE_TEXT: "FREE_TEXT", EMAIL: "EMAIL" });

    const [first, second] = out.items;
    expect(first?.created_by_name).toBe("Amruta Shukla");
    expect(first?.nested?.request_text).toBe("Please send my file.");
    expect(second?.contact).toBe("a@x.org");
    // Untouched: everything that was not sealed.
    expect(first?.id).toBe("1");
    expect(second?.count).toBe(4);
    expect(second?.when).toBeNull();
    expect(out.total).toBe(2);
    vi.unstubAllGlobals();
  });

  it("makes no request for a body with nothing sealed", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const body = { items: [{ full_name: "Amruta Shukla" }] };
    expect(await decryptDeep(body)).toBe(body);
    expect(fetchMock).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("leaves a value the service could not open as it arrived", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: [{ NAME }] }), // came back unchanged: skipped
      } as unknown as Response),
    );
    const out = await decryptDeep({ full_name: NAME });
    expect(out.full_name).toBe(NAME);
    vi.unstubAllGlobals();
  });
});

describe("decryptDeep when the service cannot be reached", () => {
  it("leaves every value as it arrived and says why once, rather than failing the page", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ error: "unreachable", service: "10.0.0.5:32688" }),
      } as unknown as Response),
    );
    const body = { items: [{ full_name: NAME, email: EMAIL }], total: 1 };
    const out = await decryptDeep(body);
    expect(out.items[0]?.full_name).toBe(NAME);
    expect(out.items[0]?.email).toBe(EMAIL);
    expect(out.total).toBe(1);
    expect(error).toHaveBeenCalledTimes(1);
    expect(String(error.mock.calls[0]?.[0])).toContain("10.0.0.5:32688");
    expect(String(error.mock.calls[0]?.[0])).not.toContain(NAME);
    error.mockRestore();
    vi.unstubAllGlobals();
  });
});
