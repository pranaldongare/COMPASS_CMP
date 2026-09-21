/**
 * The hook a page uses to read a list whose fields are encrypted.
 *
 * It exists to make the right thing the easy thing. The wrong thing is a
 * component that decrypts its own field, because a table of two hundred rows
 * then makes two hundred round trips to the key service and the page takes a
 * minute. This takes the whole list and makes one call.
 *
 * Three states, and a page has to render all three: pending while the call is
 * out, error when the key service is unreachable or the session has ended, and
 * the records themselves. A blank where a name should be, with nothing said, is
 * the failure this is written to avoid - it reads as "there is no name here"
 * rather than "this did not load".
 */

"use client";

import { useQuery } from "@tanstack/react-query";

import { decryptRecords, isEncrypted, type KeyMap } from "@/features/dkms/api";

/** Separators for the fingerprint below: two characters that cannot occur in a
 *  base64 ciphertext, so two different lists cannot collide into one key. */
const FIELD_SEP = "\u0001";
const ROW_SEP = "\u0002";

/**
 * Decrypt a list once, and keep the answer for as long as the list is on screen.
 *
 * The query key includes the ciphertext itself, so two pages showing the same
 * rows share one answer and a row that changed is decrypted again. Nothing is
 * written to storage: TanStack holds the plaintext in memory, for this tab.
 */
export function useDecrypted<T extends Record<string, unknown>>(
  records: readonly T[] | undefined,
  key: KeyMap,
  options: { enabled?: boolean; method?: "string" | "bytes" } = {},
) {
  const { enabled = true, method = "string" } = options;
  const fields = Object.keys(key);

  const fingerprint = (records ?? [])
    .map((record) => fields.map((field) => String(record[field] ?? "")).join(FIELD_SEP))
    .join(ROW_SEP);

  const anything = (records ?? []).some((record) =>
    fields.some((field) => isEncrypted(record[field])),
  );

  const query = useQuery({
    queryKey: ["dkms", "decrypt", method, fields, fingerprint],
    queryFn: () => decryptRecords(records ?? [], key, method),
    enabled: enabled && (records?.length ?? 0) > 0 && (anything || method === "bytes"),
    staleTime: Infinity,
    gcTime: 5 * 60_000,
    retry: false,
  });

  // A list with nothing encrypted in it is already readable: hand it straight
  // back rather than putting the page into a pending state for no reason.
  if (!records || records.length === 0) {
    return { data: records ?? [], isPending: false, isError: false, error: null };
  }
  if (!anything && method === "string") {
    return { data: [...records], isPending: false, isError: false, error: null };
  }
  return {
    data: query.data,
    isPending: query.isPending,
    isError: query.isError,
    error: query.error,
  };
}
