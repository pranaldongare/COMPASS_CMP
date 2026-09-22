/**
 * Reading encrypted fields, from the browser's side.
 *
 * What these pin is the behaviour that saves the page rather than the crypto,
 * which is the service's own suite: one request for a whole list, no request at
 * all when there is nothing to decrypt, order preserved, and a failure that is
 * visible rather than a blank where a name should be.
 */

import { describe, expect, it, vi } from "vitest";

import { decryptRecords, isEncrypted } from "@/lib/dkms";

function answerWith(data: unknown[], status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: async () => ({ data }),
  } as unknown as Response);
}

describe("isEncrypted", () => {
  it("knows ciphertext by its prefix, and is not fooled by anything else", () => {
    expect(isEncrypted("SE::abc")).toBe(true);
    expect(isEncrypted("Amruta Shukla")).toBe(false);
    expect(isEncrypted(null)).toBe(false);
    expect(isEncrypted(42)).toBe(false);
    expect(isEncrypted(undefined)).toBe(false);
  });
});

describe("decryptRecords", () => {
  it("sends one request for the whole list, not one per row", async () => {
    const fetchMock = answerWith([
      { id: "1", fullName: "Amruta Shukla" },
      { id: "2", fullName: "Anuj Kumar" },
    ]);
    vi.stubGlobal("fetch", fetchMock);

    const out = await decryptRecords(
      [
        { id: "1", fullName: "SE::aaa" },
        { id: "2", fullName: "SE::bbb" },
      ],
      { fullName: "NAME" },
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(out.map((r) => r.fullName)).toEqual(["Amruta Shukla", "Anuj Kumar"]);
    const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(body.key).toEqual({ fullName: "NAME" });
    expect(body.data).toHaveLength(2);
    vi.unstubAllGlobals();
  });

  it("makes no request at all when nothing is encrypted", async () => {
    const fetchMock = answerWith([]);
    vi.stubGlobal("fetch", fetchMock);

    const rows = [{ id: "1", fullName: "Amruta Shukla" }];
    const out = await decryptRecords(rows, { fullName: "NAME" });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(out).toEqual(rows);
    vi.unstubAllGlobals();
  });

  it("goes to this portal's own server, never to the key service", async () => {
    const fetchMock = answerWith([{ fullName: "x" }]);
    vi.stubGlobal("fetch", fetchMock);

    await decryptRecords([{ fullName: "SE::aaa" }], { fullName: "NAME" });

    expect(fetchMock.mock.calls[0][0]).toBe("/dkms/decrypt");
    vi.unstubAllGlobals();
  });

  it("says the session ended, rather than showing a blank", async () => {
    vi.stubGlobal("fetch", answerWith([], 401));

    await expect(
      decryptRecords([{ fullName: "SE::a" }], { fullName: "NAME" }),
    ).rejects.toThrow(/sign in again/i);
    vi.unstubAllGlobals();
  });

  it("says the service could not be reached, rather than showing a blank", async () => {
    vi.stubGlobal("fetch", answerWith([], 503));

    await expect(
      decryptRecords([{ fullName: "SE::a" }], { fullName: "NAME" }),
    ).rejects.toThrow(/could not reach the encryption service/i);
    vi.unstubAllGlobals();
  });

  it("says it could not decrypt, rather than showing a blank", async () => {
    vi.stubGlobal("fetch", answerWith([], 502));

    await expect(
      decryptRecords([{ fullName: "SE::a" }], { fullName: "NAME" }),
    ).rejects.toThrow(/could not decrypt/i);
    vi.unstubAllGlobals();
  });

  it("returns an empty list without asking anybody", async () => {
    const fetchMock = answerWith([]);
    vi.stubGlobal("fetch", fetchMock);

    expect(await decryptRecords([], { fullName: "NAME" })).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

const NAME = "SE::REsBAQNY0o7rJCgfEWj-d0FITi5nT2bKzXhQ3pOGL9Hk8w1YtmJY";

describe("decryptRecords sends the contract and nothing beyond it", () => {
  it("posts exactly {data, key, method}, so any conforming key service can answer", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: [{ NAME: "Amruta" }] }),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);
    await decryptRecords([{ NAME }], { NAME: "NAME" });
    const sent = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(Object.keys(sent).sort()).toEqual(["data", "key", "method"]);
    vi.unstubAllGlobals();
  });

  it("names the service and its answer when decryption fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => ({
          error: "decryption failed",
          service: "10.0.0.5:32688",
          status: 422,
        }),
      } as unknown as Response),
    );
    await expect(decryptRecords([{ NAME }], { NAME: "NAME" })).rejects.toThrow(
      "Could not decrypt these values (10.0.0.5:32688, answered 422).",
    );
    vi.unstubAllGlobals();
  });
});
