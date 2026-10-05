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

import { DecryptError, decryptRecords, isEncrypted, type DataType } from "@/lib/dkms/api";
import { TYPE_BY_FIELD } from "@/lib/dkms/field-types";

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

function collect(node: unknown, path: Path, out: Found[], field?: string): void {
  if (typeof node === "string") {
    if (isEncrypted(node)) {
      // The envelope says which type it is, when the key service that wrote
      // it writes this envelope. When it does not - another service, sealing
      // the same data under the same contract - the field's own name says
      // it instead. Without that fallback such a value was skipped in
      // silence and the page showed `SE::…` where a name should be.
      const type = typeOf(node) ?? (field ? TYPE_BY_FIELD[field] : undefined);
      if (type) out.push({ path, value: node, type });
      else if (field) unlabelled.add(field);
    }
    return;
  }
  if (Array.isArray(node)) {
    node.forEach((item, i) => collect(item, [...path, i], out, field));
    return;
  }
  if (node && typeof node === "object") {
    for (const [k, v] of Object.entries(node)) collect(v, [...path, k], out, k);
  }
}

/**
 * Fields seen sealed that nothing could label, reported once each.
 *
 * Silence here is the failure that looks like a rendering bug: the value
 * stays `SE::…` on the page and no request is ever made for it. One line
 * per field name, never a value, and only the first time.
 */
const unlabelled = new Set<string>();

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
  const before = unlabelled.size;
  collect(body, [], found);
  if (unlabelled.size > before) {
    console.error(
      `[dkms] sealed value(s) no type could be read for, left as they arrived: ` +
        `${[...unlabelled].join(", ")}. Either the key service writes a different ` +
        `envelope, or these fields are missing from lib/dkms/field-types.ts.`,
    );
  }
  if (found.length === 0) return body;

  const records = found.map((f) => ({ [f.type]: f.value }));
  const key = Object.fromEntries(found.map((f) => [f.type, f.type])) as Record<
    string,
    DataType
  >;
  // The service may refuse the batch because one value in it is not something
  // it can open - a blob cut short, glued to other text, sealed under a key it
  // does not hold. A page should not lose two hundred names to one bad one, so
  // a refused batch is split in halves until the bad ones are alone. Anything
  // else - throttled, unreachable, signed out, failing - is not asked again:
  // the page renders with `SE::...` where the values are, visibly wrong and
  // therefore reported, rather than failing on every screen at once.
  const run: Narrowing = { calls: 0, refused: 0, stopped: null };
  const opened = await narrow(records, key, run);
  if (run.stopped) {
    // One line, never a value.
    console.error(`[dkms] value(s) left sealed: ${describe(run.stopped)}`);
  }
  if (run.refused > 0) {
    console.error(`[dkms] ${run.refused} of ${records.length} value(s) could not be opened`);
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

/**
 * The most calls one response may cost while narrowing down refused values.
 * Halving finds one bad value among n in about 2·log2(n) calls - 20 for a
 * page of 600 - and the cap bounds a page where many are bad. Before
 * October 2026 a refused batch was retried one value per request, all at
 * once: 601 requests for a page of 600 (review SCALE-4).
 */
const MAX_CALLS = 48;

interface Narrowing {
  calls: number;
  refused: number;
  stopped: unknown;
}

/**
 * Open `records`, halving a batch the service refuses or finds too large.
 *
 * One call at a time, never in parallel, and the first failure that is not
 * about the values themselves stops the whole run: a throttled or failing
 * service is not asked again. Whatever is not opened comes back as it
 * arrived, and setAt leaves the sealed value in place.
 */
async function narrow(
  records: Record<string, string>[],
  key: Record<string, DataType>,
  run: Narrowing,
): Promise<Record<string, string>[]> {
  if (run.stopped || records.length === 0) return records;
  if (run.calls >= MAX_CALLS) {
    run.stopped = new Error(`gave up after ${MAX_CALLS} calls`);
    return records;
  }
  run.calls += 1;
  try {
    return await decryptRecords(records, key);
  } catch (cause) {
    const splittable =
      cause instanceof DecryptError &&
      (cause.failure === "refused" || cause.failure === "too_large");
    if (!splittable) {
      run.stopped = cause;
      return records;
    }
    if (records.length === 1) {
      run.refused += 1;
      return records;
    }
    const half = Math.ceil(records.length / 2);
    const left = await narrow(records.slice(0, half), key, run);
    const right = await narrow(records.slice(half), key, run);
    return [...left, ...right];
  }
}
