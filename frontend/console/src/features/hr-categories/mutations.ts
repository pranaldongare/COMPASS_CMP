/**
 * Writing the Legal office's categories (0052). A category's page reads it
 * whole, so every write refreshes the detail and the lists; an HR PoC's
 * assignments refresh their account page too.
 */
"use client";

import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as api from "@/features/hr-categories/api";
import { keys, type Result } from "@/lib/query";
import type { CategoryProcessor, HrCategory, PocCategory, Uuid } from "@/types";

function settle(qc: QueryClient, uuid?: Uuid) {
  void qc.invalidateQueries({ queryKey: ["hr-categories"] });
  if (uuid) void qc.invalidateQueries({ queryKey: keys.hrCategory.detail(uuid) });
}

export function useCreateHrCategory(): Result<HrCategory, api.HrCategoryInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createHrCategory,
    onSuccess: (c) => settle(qc, c.category_uuid),
  });
}

export function useUpdateHrCategory(
  uuid: Uuid,
): Result<HrCategory, Parameters<typeof api.updateHrCategory>[1]> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => api.updateHrCategory(uuid, body),
    onSuccess: () => settle(qc, uuid),
  });
}

export function useSetHrCategoryStatus(
  uuid: Uuid,
): Result<HrCategory, "active" | "retired"> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (status) => api.setHrCategoryStatus(uuid, status),
    onSuccess: () => settle(qc, uuid),
  });
}

export function useSetCategoryProcessors(
  uuid: Uuid,
): Result<CategoryProcessor[], api.CategoryProcessorInput[]> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (processors) => api.setCategoryProcessors(uuid, processors),
    onSuccess: () => settle(qc, uuid),
  });
}

/** An HR PoC's categories, set by the administrator on the account's page. */
export function useSetUserCategories(userUuid: Uuid): Result<PocCategory[], Uuid[]> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (categoryUuids) => api.setUserCategories(userUuid, categoryUuids),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.users.detail(userUuid) });
      void qc.invalidateQueries({ queryKey: ["hr-categories"] });
      void qc.invalidateQueries({ queryKey: ["hr-category"] });
      void qc.invalidateQueries({ queryKey: ["hr-pocs"] });
    },
  });
}
