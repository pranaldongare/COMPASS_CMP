/**
 * The signed-in user editing their own profile.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { UpdateMeInput } from "@/features/account/api";
import {
  removeSecondaryEmail,
  requestContactCode,
  setPersonType,
  updateMe,
  verifyContact,
} from "@/features/account/api";
import type { Result } from "@/lib/query";
import { keys } from "@/lib/query";
import type { Acknowledged, MeProfile } from "@/types";

export function useUpdateMe(): Result<MeProfile, UpdateMeInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: updateMe,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.auth.me }),
  });
}

/** Nothing about the account changes when a code is sent, so nothing is invalidated. */
export function useRequestContactCode(): Result<Acknowledged, string> {
  return useMutation({ mutationFn: requestContactCode });
}

export function useVerifyContact(): Result<
  Acknowledged,
  { contact: string; code: string }
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: verifyContact,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.auth.me }),
  });
}

export function useRemoveSecondaryEmail(): Result<Acknowledged, void> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => removeSecondaryEmail(),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.auth.me }),
  });
}

export function useSetPersonType(): Result<
  Acknowledged,
  { person_type: string; reason?: string }
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: setPersonType,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.auth.me }),
  });
}
