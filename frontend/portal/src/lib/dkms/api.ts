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

  const response = await fetch("/dkms/decrypt", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ data: records, key, method }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Your session has ended — sign in again to read these.");
    }
    const detail = (await response.json().catch(() => ({}))) as {
      service?: string;
      status?: number;
    };
    const where = detail.service ? ` (${detail.service}` : "";
    const upstream = detail.status ? `, answered ${detail.status})` : where ? ")" : "";
    throw new Error(
      response.status === 503
        ? `Could not reach the encryption service${where}${upstream}.`
        : `Could not decrypt these values${where}${upstream}.`,
    );
  }

  const body = (await response.json()) as { data: T[] };
  return body.data;
}
