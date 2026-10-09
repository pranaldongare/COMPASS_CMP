/**
 * Administering user accounts, roles and sessions.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  changeUserRole,
  createUser,
  deactivateUser,
  forceLogout,
  reactivateUser,
  resendInvitation,
  resetMfa,
  setUserProcessors,
  updateUser,
  type UserInput,
} from "@/features/users/api";
import type { ApiError } from "@/lib/errors";
import { keys, type Result } from "@/lib/query";
import type { Acknowledged, CollectorProcessor, User, Uuid } from "@/types";

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation<Acknowledged, ApiError, Uuid>({
    mutationFn: deactivateUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.users.all }),
  });
}

export function useReactivateUser() {
  const qc = useQueryClient();
  return useMutation<Acknowledged, ApiError, Uuid>({
    mutationFn: reactivateUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.users.all }),
  });
}

export function useCreateUser(): Result<User, UserInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.users.all }),
  });
}

export function useUpdateUser(uuid: Uuid): Result<User, Partial<UserInput>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<UserInput>) => updateUser(uuid, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.users.all }),
  });
}

/** A DCO's or an RCO's processors. What they see in Data Sources follows. */
export function useSetUserProcessors(uuid: Uuid): Result<CollectorProcessor[], string[]> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (processorUuids: string[]) => setUserProcessors(uuid, processorUuids),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.users.all });
      void qc.invalidateQueries({ queryKey: ["processors"] });
      void qc.invalidateQueries({ queryKey: ["sources"] });
      void qc.invalidateQueries({ queryKey: keys.users.collectionOwners });
    },
  });
}

export function useChangeRole(
  uuid: Uuid,
): Result<Acknowledged, { role: string; reason?: string }> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { role: string; reason?: string }) => changeUserRole(uuid, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.users.all }),
  });
}

/**
 * Send the invitation again.
 *
 * Deliberately does not invalidate the register: nothing about the account row
 * changed, and a refetch would suggest to the administrator that it did.
 */
export function useResendInvitation(): Result<Acknowledged, Uuid> {
  return useMutation({ mutationFn: resendInvitation });
}

export function useResetMfa(): Result<Acknowledged, Uuid> {
  return useMutation({
    mutationFn: resetMfa,
  });
}

/**
 * End every session this user holds.
 *
 * The response to a lost laptop, so it deliberately does not invalidate the
 * user list: nothing about the account row changed, and refetching would
 * suggest to the administrator that something did.
 */
export function useForceLogout(): Result<Acknowledged, Uuid> {
  return useMutation({ mutationFn: forceLogout });
}
