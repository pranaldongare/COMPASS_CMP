/** Reading the Legal office's categories (0052). */
"use client";

import { useQuery } from "@tanstack/react-query";

import { getHrCategory, listHrCategories, listHrPocs } from "@/features/hr-categories/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { HrCategory, HrCategoryDetail, HrPoc, Uuid } from "@/types";

export function useHrCategories(
  filters: { status?: string; q?: string } = {},
  { enabled = true }: { enabled?: boolean } = {},
) {
  return useQuery<HrCategory[], ApiError>({
    queryKey: keys.hrCategory.list(filters),
    queryFn: () => listHrCategories(filters),
    enabled,
  });
}

export function useHrCategory(uuid: Uuid | undefined) {
  return useQuery<HrCategoryDetail, ApiError>({
    queryKey: keys.hrCategory.detail(uuid ?? ""),
    queryFn: () => getHrCategory(uuid!),
    enabled: Boolean(uuid),
  });
}

export function useHrPocs(filters: { category?: Uuid } = {}, enabled = true) {
  return useQuery<HrPoc[], ApiError>({
    queryKey: keys.hrCategory.pocs(filters),
    queryFn: () => listHrPocs(filters),
    enabled,
  });
}
