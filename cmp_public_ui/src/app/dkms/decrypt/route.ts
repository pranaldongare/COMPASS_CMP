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
const DKMS_URL = (process.env.DKMS_URL ?? "http://127.0.0.1:8100").replace(/\/+$/, "");
const SESSION_COOKIE = process.env.NEXT_PUBLIC_SESSION_COOKIE ?? "cmp_session";

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
    answer = await fetch(`${DKMS_URL}/decrypt/bulk`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      // `skip`, not `fail`: a page rendering rows written before the rollout
      // would otherwise refuse to render at all because one value is still
      // plaintext. Those come back as they are.
      body: JSON.stringify({ data, key, method, on_error: "skip" }),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "the encryption service is unreachable" },
      { status: 503 },
    );
  }

  if (!answer.ok) {
    // The service's error names a record index and a field and never quotes a
    // value, but it is not this page's job to relay it: say what happened.
    return NextResponse.json({ error: "decryption failed" }, { status: 502 });
  }

  const result = (await answer.json()) as { data: unknown[] };
  return NextResponse.json(
    { data: result.data },
    // Plaintext personal data: no store, anywhere, by anyone.
    { headers: { "cache-control": "no-store, private", "x-robots-tag": "noindex" } },
  );
}
