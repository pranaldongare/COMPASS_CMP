/**
 * Decryption, on the server side of this portal.
 *
 * The brief was that decryption happens in the frontend layer rather than in
 * the platform API — so that the API stores and serves ciphertext and never
 * holds the plaintext it is protecting. This is that layer, and it runs in the
 * portal's **server**, never in the browser.
 *
 * That distinction is the whole security of the arrangement. If the browser
 * called the key service directly, then every person with a session would hold
 * a general-purpose decryption oracle: paste in any ciphertext from anywhere,
 * get plaintext back, for rows they were never allowed to read. Here, the
 * browser sends ciphertext it was *already served* by the API — which means it
 * already passed the permission matrix, the scope in the WHERE clause and the
 * 404-for-out-of-scope rule — and this handler exchanges it for plaintext.
 *
 * Three things it insists on:
 *
 * 1. **A session.** No cookie, no decryption. The cookie is HttpOnly and this
 *    is the server, so it can be read here and cannot be read by page script.
 * 2. **A batch.** One call per page render, not one per field. The key service
 *    parallelises across its pool, so a list of two hundred rows costs about
 *    what one row costs.
 * 3. **Silence.** Nothing is logged: not the ciphertext, not the plaintext,
 *    not the field names. A log line here would undo the exercise.
 *
 * `DKMS_URL` is server-only and deliberately not `NEXT_PUBLIC_`: the browser
 * must not know where the key service is, let alone reach it.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Server-only. The key service is not on the public internet and not in the bundle. */
const DKMS_URL = (process.env.DKMS_URL ?? "http://localhost:32688").replace(/\/+$/, "");
const SESSION_COOKIE = process.env.NEXT_PUBLIC_SESSION_COOKIE ?? "cmp_session";

/** The host alone, for a diagnostic: never the path, never a value. */
const HOST = (() => {
  try {
    return new URL(DKMS_URL).host;
  } catch {
    return "invalid DKMS_URL";
  }
})();

/** A key service on another machine answers in milliseconds; a hung one
 *  must not hold a page for the fetch default of forever. */
const TIMEOUT_MS = 10_000;

/** Matches the service's own ceiling, so a refusal happens here rather than there. */
const MAX_RECORDS = 5000;

interface DecryptBody {
  data?: unknown;
  key?: unknown;
  method?: "string" | "bytes";
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!request.cookies.get(SESSION_COOKIE)) {
    // Not an authorisation decision — the API made that when it served the
    // ciphertext. This only refuses to be an open oracle.
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  let body: DecryptBody;
  try {
    body = (await request.json()) as DecryptBody;
  } catch {
    return NextResponse.json({ error: "not JSON" }, { status: 400 });
  }

  const { data, key, method = "string" } = body;
  if (!Array.isArray(data) || typeof key !== "object" || key === null) {
    return NextResponse.json({ error: "expected { data: [], key: {} }" }, { status: 400 });
  }
  if (data.length === 0) return NextResponse.json({ data: [] });
  if (data.length > MAX_RECORDS) {
    return NextResponse.json(
      { error: `${data.length} records; the limit is ${MAX_RECORDS}` },
      { status: 413 },
    );
  }

  let answer: Response;
  try {
    answer = await fetch(`${DKMS_URL}/bulk_decrypt`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      // The contract and nothing beyond it - `{data, key, method}` - so any
      // key service that speaks it can stand behind this route, not only the
      // one in this repository. Only sealed values are ever sent (the walker
      // collects `SE::` strings and nothing else), so there is no plaintext
      // for a strict service to refuse.
      body: JSON.stringify({ data, key, method }),
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (cause) {
    // One line, naming the host and the failure and never a value, so the
    // person who pointed DKMS_URL somewhere can see whether it was reached.
    console.error(
      `[dkms] ${DKMS_URL}/bulk_decrypt unreachable: ${cause instanceof Error ? cause.message : "error"}`,
    );
    return NextResponse.json(
      { error: "the encryption service is unreachable", service: HOST },
      { status: 503 },
    );
  }

  if (!answer.ok) {
    // The service's error names a record index and a field and never quotes a
    // value, but it is not this page's job to relay it: say what happened.
    console.error(`[dkms] ${DKMS_URL}/bulk_decrypt answered ${answer.status}`);
    return NextResponse.json(
      { error: "decryption failed", service: HOST, status: answer.status },
      { status: 502 },
    );
  }

  const result = (await answer.json()) as { data: unknown[] };
  return NextResponse.json(
    { data: result.data },
    // Plaintext personal data: no store, anywhere, by anyone.
    { headers: { "cache-control": "no-store, private", "x-robots-tag": "noindex" } },
  );
}
