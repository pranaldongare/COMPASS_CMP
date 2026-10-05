/**
 * The browser's half of decryption: one call, for a whole list.
 *
 * It talks to this portal's own `/dkms/decrypt`, never to the key service. The
 * browser does not know where that is and could not reach it if it did.
 */

/** The DKMS vocabulary. Mirrors `backend/dkms/app/dkms/types.py`. */
export type DataType =
  | "NAME"
  | "EMAIL"
  | "MOBILE"
  | "CONTACT"
  | "DOB"
  | "ORG_ID"
  | "PERSON_TYPE"
  | "ADDRESS"
  | "IP"
  | "FREE_TEXT"
  | "FILE_NAME"
  | "GOVT_ID"
  | "GENERIC";

/** Which fields of a record to decrypt, and what each was written as. */
export type KeyMap = Record<string, DataType>;

/**
 * Why a decrypt call failed, as something a caller can act on.
 *
 * - `refused`: the key service answered 400 or 422 - something in the batch
 *   is not a value it can open. The rest of the batch may be fine.
 * - `too_large`: more records than the route takes in one call (413).
 * - `throttled`: the service said 429. Asking again now makes it worse.
 * - `unreachable`: no answer from the service, or from this route (503, or
 *   the fetch itself failed).
 * - `signed_out`: the route answered 401.
 * - `failed`: anything else - the service erred, or the request was wrong.
 *
 * Only the first two are worth another, smaller request (review SCALE-4).
 */
export type DecryptFailure =
  | "refused"
  | "too_large"
  | "throttled"
  | "unreachable"
  | "signed_out"
  | "failed";

export class DecryptError extends Error {
  constructor(
    message: string,
    readonly failure: DecryptFailure,
  ) {
    super(message);
    this.name = "DecryptError";
  }
}

/** Is this value DKMS ciphertext? Cheap, and the reason a page can skip a call. */
export function isEncrypted(value: unknown): value is string {
  return typeof value === "string" && value.startsWith("SE::");
}

/**
 * Decrypt the named fields of every record, in one request.
 *
 * Returns the records in the order they were given, which is what every caller
 * lines up by. Records with nothing encrypted in them are returned untouched
 * and cost nothing: if no record carries ciphertext, no request is made at all.
 */
export async function decryptRecords<T extends Record<string, unknown>>(
  records: readonly T[],
  key: KeyMap,
  method: "string" | "bytes" = "string",
): Promise<T[]> {
  if (records.length === 0) return [];

  const fields = Object.keys(key);
  const needed =
    method === "bytes" ||
    records.some((record) => fields.some((field) => isEncrypted(record[field])));
  if (!needed) return [...records];

  let response: Response;
  try {
    response = await fetch("/dkms/decrypt", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ data: records, key, method }),
    });
  } catch {
    throw new DecryptError("Could not reach the encryption service.", "unreachable");
  }

  if (!response.ok) {
    if (response.status === 401) {
      throw new DecryptError(
        "Your session has ended — sign in again to read these.",
        "signed_out",
      );
    }
    const detail = (await response.json().catch(() => ({}))) as {
      service?: string;
      status?: number;
    };
    const where = detail.service ? ` (${detail.service}` : "";
    const upstream = detail.status ? `, answered ${detail.status})` : where ? ")" : "";
    throw new DecryptError(
      response.status === 503
        ? `Could not reach the encryption service${where}${upstream}.`
        : `Could not decrypt these values${where}${upstream}.`,
      failureOf(response.status, detail.status),
    );
  }

  const body = (await response.json()) as { data: T[] };
  return body.data;
}

function failureOf(status: number, upstream: number | undefined): DecryptFailure {
  if (status === 503) return "unreachable";
  if (status === 413) return "too_large";
  if (status !== 502 || upstream === undefined) return "failed";
  if (upstream === 400 || upstream === 422) return "refused";
  if (upstream === 413) return "too_large";
  if (upstream === 429) return "throttled";
  return "failed";
}
