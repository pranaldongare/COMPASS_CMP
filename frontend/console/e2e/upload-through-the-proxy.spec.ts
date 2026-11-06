/**
 * A file the forms allow gets through the console's own proxy.
 *
 * The forms take 25 MB, and every upload goes through the `/api` rewrite. Left
 * at its defaults, that forwards the first 10 MB of a body while the
 * Content-Length still promises the rest, so the API waits for bytes that never
 * come and the proxy answers 500 after 30 seconds.
 *
 * The API's 404 is the proof. FastAPI reads the whole form before it looks for
 * the breach, so it answers only if every byte arrived, and with no such breach
 * nothing is stored.
 */
import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import fs from "node:fs";

import { statePath } from "./support/session";

test.use({ storageState: statePath("dpo") });

test("a 20 MB file reaches the API whole", async ({ request }) => {
  test.setTimeout(60_000);
  const state = JSON.parse(fs.readFileSync(statePath("dpo"), "utf8")) as {
    cookies: Array<{ name: string; value: string }>;
  };
  const csrf = state.cookies.find((c) => c.name === "cmp_csrf")?.value ?? "";

  const response = await request.post(`/api/breaches/${randomUUID()}/attachments`, {
    headers: { "X-CSRF-Token": csrf },
    multipart: {
      kind: "proof",
      file: { name: "scan.pdf", mimeType: "application/pdf", buffer: Buffer.alloc(20 * 1024 * 1024, 0x20) },
    },
  });

  expect(response.status()).toBe(404);
  // The API's own answer about the breach, not a path nothing serves.
  expect(((await response.json()) as { error: { message: string } }).error.message).toBe("Breach not found");
});
