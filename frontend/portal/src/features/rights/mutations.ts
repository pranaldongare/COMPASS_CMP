/**
 * Writing to a rights request, as the data principal.
 *
 * Every write she makes invalidates everything under `["me"]` - her requests,
 * her nominations, her consents - and the dashboard. One helper, so a new
 * action cannot forget one of them.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import * as api from "@/features/rights/api";
import { keys, type Result } from "@/lib/query";
import type { MyRequest, Nomination, Uuid } from "@/types";

/* ------------------------------------------------------ the principal */

function useInvalidateMine() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: ["me"] });
    void qc.invalidateQueries({ queryKey: keys.dashboard.all });
  };
}

export function useMakeRequest(): Result<MyRequest, api.MyRequestInput> {
  const invalidate = useInvalidateMine();
  return useMutation({ mutationFn: api.makeRequest, onSuccess: invalidate });
}

export function useDispute(uuid: Uuid): Result<MyRequest, { text: string; about_dpo?: boolean }> {
  const invalidate = useInvalidateMine();
  return useMutation({
    mutationFn: (body: { text: string; about_dpo?: boolean }) => api.disputeRequest(uuid, body),
    onSuccess: invalidate,
  });
}

export function useNominate(): Result<Nomination, api.NominationInput> {
  const invalidate = useInvalidateMine();
  return useMutation({ mutationFn: api.nominate, onSuccess: invalidate });
}

export function useRevokeNomination(): Result<Nomination, Uuid> {
  const invalidate = useInvalidateMine();
  return useMutation({ mutationFn: api.revokeNomination, onSuccess: invalidate });
}
