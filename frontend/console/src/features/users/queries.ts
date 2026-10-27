/**
 * Reading the user directory.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getUser,
  listOffices,
  listPersonTypeHistory,
  listStaff,
  listUsers,
} from "@/features/users/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type {
  Office,
  Page,
  PersonTypeHistoryEntry,
  StaffMember,
  User,
  Uuid,
} from "@/types";

export function useUsers(filters: Record<string, unknown> = {}) {
  return useQuery<Page<User>, ApiError>({
    queryKey: keys.users.list(filters),
    queryFn: () => listUsers(filters),
  });
}

export function useStaff(enabled = true) {
  return useQuery<StaffMember[], ApiError>({
    queryKey: keys.users.staff,
    queryFn: listStaff,
    enabled,
  });
}

/** The two offices (ADR 0032). Rows, not a constant: a third is an INSERT. */
export function useOffices() {
  return useQuery<Office[], ApiError>({
    queryKey: keys.users.offices,
    queryFn: listOffices,
    staleTime: Infinity,
  });
}

/** One account, for its own page (2026-10-09). */
export function useUser(uuid: Uuid | undefined) {
  return useQuery<User, ApiError>({
    queryKey: keys.users.detail(uuid ?? ""),
    queryFn: () => getUser(uuid!),
    enabled: Boolean(uuid),
  });
}

export function usePersonTypeHistory(uuid: Uuid | undefined) {
  return useQuery<PersonTypeHistoryEntry[], ApiError>({
    queryKey: keys.users.personTypeHistory(uuid ?? ""),
    queryFn: () => listPersonTypeHistory(uuid!),
    enabled: Boolean(uuid),
  });
}
