/**
 * An upload gets longer than the 30-second default (Option 2 relay PoC).
 *
 * A 25 MB file over a mobile connection cannot finish in 30 s, and with the
 * portal on AWS it also crosses the relay's queue. The request interceptor
 * gives a multipart body `UPLOAD_TIMEOUT_MS` and leaves every other request
 * on the default.
 *
 * Portal-only on purpose: `client.test.ts` is shared byte-for-byte with the
 * console (frontend/shared-files.txt), whose client this change does not touch.
 * The adapter stands in for the network and sees the config exactly as the
 * interceptors left it.
 */

import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios";
import { describe, expect, it } from "vitest";

import { UPLOAD_TIMEOUT_MS, apiGet, apiPost } from "@/lib/api/client";

function capture(): { adapter: AxiosAdapter; seen: InternalAxiosRequestConfig[] } {
  const seen: InternalAxiosRequestConfig[] = [];
  const adapter: AxiosAdapter = async (config) => {
    seen.push(config);
    return { data: {}, status: 200, statusText: "OK", headers: {}, config };
  };
  return { adapter, seen };
}

describe("the request timeout", () => {
  it("is 180 seconds for a multipart upload", async () => {
    const { adapter, seen } = capture();
    const form = new FormData();
    form.append("file", new Blob(["%PDF-1.7"], { type: "application/pdf" }), "proof.pdf");

    await apiPost("/me/requests/r1/attachments", form, { adapter });

    expect(UPLOAD_TIMEOUT_MS).toBe(180_000);
    expect(seen[0]?.timeout).toBe(UPLOAD_TIMEOUT_MS);
    // The browser still writes the multipart boundary itself.
    expect(String(seen[0]?.headers.get("Content-Type") ?? "")).not.toContain(
      "application/json",
    );
  });

  it("stays at the 30-second default for everything else", async () => {
    const { adapter, seen } = capture();

    await apiPost("/me/requests", { kind: "access" }, { adapter });
    await apiGet("/me/consents", { adapter });

    expect(seen.map((config) => config.timeout)).toEqual([30_000, 30_000]);
  });

  it("never shortens a longer timeout a caller asked for", async () => {
    const { adapter, seen } = capture();

    await apiPost("/me/requests/r1/attachments", new FormData(), {
      adapter,
      timeout: 300_000,
    });

    expect(seen[0]?.timeout).toBe(300_000);
  });
});
