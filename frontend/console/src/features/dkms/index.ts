/**
 * Reading encrypted fields, from a page.
 *
 * The primitives - `decryptRecords`, `isEncrypted`, `decryptDeep` - live in
 * `lib/dkms`, because the API client uses them. This re-exports them so a page
 * has one import, and adds the hook.
 */

export * from "@/lib/dkms";
export * from "@/features/dkms/use-decrypted";
