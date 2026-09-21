/**
 * Reading sealed personal data: the primitives.
 *
 * In `lib` because the API client depends on them, and `lib` is the bottom
 * layer. The React hook that pages use is in `features/dkms`.
 */

export * from "@/lib/dkms/api";
export * from "@/lib/dkms/deep";
