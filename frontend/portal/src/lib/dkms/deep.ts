/**
 * Decrypting whatever a response happens to carry, wherever it carries it.
 *
 * The API stores and serves personal columns sealed - `SE::` followed by an
 * envelope - and this portal is where they are opened. A page-by-page approach
 * would mean every list, every card and every detail view knowing which of its
 * fields are sealed, and one forgotten field would show a person a string of
 * base64 where a name should be. So it is done once, for every response, at
 * the API client: walk the body, find every sealed string, open them all in
 * one call, put them back.
 *
 * **The type is read off the envelope.** Byte 3 of the header says what the
 * value was encrypted as - a NAME, an EMAIL, FREE_TEXT - so the request to the
 * key service can name the right type without this code knowing which field
 * is which. That is what makes the walk generic: `created_by_name` three
 * levels deep in a project and `full_name` at the top of a user are the same
 * case.
 *
 * **One call per response.** Every sealed value in the body, whatever its
 * type, travels in one request as `[{NAME: c1}, {FREE_TEXT: c2}, ...]` with a
 * key naming every type once. A page of two hundred rows with three sealed
 * columns each is one round trip.
 */

import { decryptRecords, isEncrypted, type DataType } from "@/lib/dkms/api";

/** Byte 3 of the envelope, mirroring TYPE_IDS in the key service. */
const TYPE_BY_ID: Record<number, DataType> = {
  1: "NAME",
  2: "EMAIL",
  3: "MOBILE",
  4: "CONTACT",
  5: "DOB",
  6: "ORG_ID",
  7: "PERSON_TYPE",
  8: "ADDRESS",
  9: "IP",
  10: "FREE_TEXT",
  11: "FILE_NAME",
  12: "GOVT_ID",
  13: "GENERIC",
};

/** The type a sealed value was written as, or null if it is not one of ours. */
export function typeOf(sealed: string): DataType | null {
  if (!sealed.startsWith("SE::")) return null;
  // The first eight base64url characters hold the first six bytes: 'D' 'K'
  // version type nonce[0] nonce[1]. Standard alphabet for atob.
  const head = sealed.slice(4, 12).replace(/-/g, "+").replace(/_/g, "/");
  let bytes: string;
  try {
    bytes = atob(head);
  } catch {
    return null;
  }
  if (bytes.length < 4 || bytes.charCodeAt(0) !== 0x44 || bytes.charCodeAt(1) !== 0x4b)
    return null;
  return TYPE_BY_ID[bytes.charCodeAt(3)] ?? null;
}

type Path = (string | number)[];

interface Found {
  path: Path;
  value: string;
  type: DataType;
}

function collect(node: unknown, path: Path, out: Found[]): void {
  if (typeof node === "string") {
    if (isEncrypted(node)) {
      const type = typeOf(node);
      if (type) out.push({ path, value: node, type });
    }
    return;
  }
  if (Array.isArray(node)) {
    node.forEach((item, i) => collect(item, [...path, i], out));
    return;
  }
  if (node && typeof node === "object") {
    for (const [k, v] of Object.entries(node)) collect(v, [...path, k], out);
  }
}

function setAt(root: unknown, path: Path, value: unknown): void {
  let node = root as Record<string | number, unknown>;
  for (let i = 0; i < path.length - 1; i++)
    node = node[path[i]] as Record<string | number, unknown>;
  node[path[path.length - 1]] = value;
}

/** Does this body carry anything sealed at all? Cheap, and usually the answer is no. */
export function hasSealed(body: unknown): boolean {
  const found: Found[] = [];
  collect(body, [], found);
  return found.length > 0;
}

/**
 * Open every sealed string in a response body, in one call, in place.
 *
 * Returns the same object it was given, mutated - the body is fresh from the
 * wire and nobody else holds it yet. A value the service could not open (a
 * key it does not hold, a tampered blob) is left as it arrived rather than
 * failing the whole page; the service reports those, and a name that reads
 * `SE::...` is at least visibly wrong rather than silently missing.
 */
export async function decryptDeep<T>(body: T): Promise<T> {
  const found: Found[] = [];
  collect(body, [], found);
  if (found.length === 0) return body;

  const records = found.map((f) => ({ [f.type]: f.value }));
  const key = Object.fromEntries(found.map((f) => [f.type, f.type])) as Record<
    string,
    DataType
  >;
  let opened: Record<string, string>[];
  try {
    opened = await decryptRecords(records, key);
  } catch (cause) {
    if (isUnreachable(cause)) {
      // Nothing to retry against. The page still renders - with `SE::...`
      // where the values are, which is visibly wrong and therefore reported -
      // rather than failing on every screen at once. One line, never a value.
      console.error(`[dkms] ${found.length} value(s) left sealed: ${describe(cause)}`);
      return body;
    }
    // The service refused the batch: one value in it is not something it can
    // open - a blob that was cut short, glued to other text, or sealed under
    // a key it does not hold. The other values are fine, and a page should
    // not lose two hundred names to one bad one. Each is asked for alone;
    // the bad ones stay as they arrived and are counted, not quoted.
    opened = await oneByOne(records, key);
  }

  found.forEach((f, i) => {
    const value = opened[i]?.[f.type];
    if (typeof value === "string") setAt(body, f.path, value);
  });
  return body;
}

function describe(cause: unknown): string {
  return cause instanceof Error ? cause.message : "unknown error";
}

function isUnreachable(cause: unknown): boolean {
  return cause instanceof Error && /could not reach|session has ended/i.test(cause.message);
}

async function oneByOne(
  records: Record<string, string>[],
  key: Record<string, DataType>,
): Promise<Record<string, string>[]> {
  const out = await Promise.all(
    records.map(async (record) => {
      const [type] = Object.keys(record) as DataType[];
      try {
        const [one] = await decryptRecords([record], { [type]: key[type] });
        return one ?? record;
      } catch {
        return record; // as it arrived; setAt keeps the sealed value in place
      }
    }),
  );
  const refused = out.filter((r, i) => r === records[i]).length;
  if (refused > 0)
    console.error(`[dkms] ${refused} of ${records.length} value(s) could not be opened`);
  return out;
}
