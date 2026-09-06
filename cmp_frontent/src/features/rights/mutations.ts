/**
 * Writing to a rights request.
 *
 * Every staff action on one request invalidates the same three things: the
 * request itself (with its holders, scope and transitions), the register, and
 * the dashboard - whose most time-bound queue this is. One factory, so a new
 * action cannot forget one of them.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import * as api from "@/features/rights/api";
import type { ApiError } from "@/lib/errors";
import { keys, prefixes, type Result } from "@/lib/query";
import type {
  GrievanceDecisionResult,
  MyRequest,
  Nomination,
  RightsHolder,
  RightsRequest,
  RightsScopeItem,
  Uuid,
} from "@/types";

function useInvalidateRequest(uuid: Uuid) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: keys.rights.detail(uuid) });
    void qc.invalidateQueries({ queryKey: prefixes.anyRequestList });
    void qc.invalidateQueries({ queryKey: keys.dashboard.all });
  };
}

function useRequestAction<TData, TVars>(
  uuid: Uuid,
  fn: (vars: TVars) => Promise<TData>,
): Result<TData, TVars> {
  const invalidate = useInvalidateRequest(uuid);
  return useMutation<TData, ApiError, TVars>({ mutationFn: fn, onSuccess: invalidate });
}

/* ------------------------------------------------------------- the DPO */

export function useLogRequest(): Result<RightsRequest, api.LogRequestInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.logRequest,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: prefixes.anyRequestList });
      void qc.invalidateQueries({ queryKey: keys.dashboard.all });
    },
  });
}

export const useAcknowledge = (uuid: Uuid) =>
  useRequestAction<RightsRequest, void>(uuid, () => api.acknowledge(uuid));
export const useSendVerificationCode = (uuid: Uuid) =>
  useRequestAction<RightsRequest, void>(uuid, () => api.sendVerificationCode(uuid));
export const useConfirmVerificationCode = (uuid: Uuid) =>
  useRequestAction<RightsRequest, string>(uuid, (code) => api.confirmVerificationCode(uuid, code));
export const useVerifyManually = (uuid: Uuid) =>
  useRequestAction<RightsRequest, string>(uuid, (note) => api.verifyManually(uuid, note));
export const useFailVerification = (uuid: Uuid) =>
  useRequestAction<RightsRequest, string | null>(uuid, (note) => api.failVerification(uuid, note));
export const useClassify = (uuid: Uuid) =>
  useRequestAction<RightsRequest, Parameters<typeof api.classify>[1]>(uuid, (body) =>
    api.classify(uuid, body),
  );
export const useRefuse = (uuid: Uuid) =>
  useRequestAction<RightsRequest, string>(uuid, (reason) => api.refuse(uuid, reason));
export const useTreatAsWithdrawal = (uuid: Uuid) =>
  useRequestAction<RightsRequest, string | null>(uuid, (note) => api.treatAsWithdrawal(uuid, note));
export const useConfirmIntent = (uuid: Uuid) =>
  useRequestAction<RightsRequest, void>(uuid, () => api.confirmIntent(uuid));
export const useRecordEvent = (uuid: Uuid) =>
  useRequestAction<RightsRequest, Parameters<typeof api.recordEvent>[1]>(uuid, (body) =>
    api.recordEvent(uuid, body),
  );
export const useEscalate = (uuid: Uuid) =>
  useRequestAction<RightsRequest, void>(uuid, () => api.escalate(uuid));
export const useAssignReviewer = (uuid: Uuid) =>
  useRequestAction<RightsRequest, Uuid>(uuid, (reviewer) => api.assignReviewer(uuid, reviewer));
export const useTransitionRequest = (uuid: Uuid) =>
  useRequestAction<RightsRequest, Parameters<typeof api.transitionRequest>[1]>(uuid, (body) =>
    api.transitionRequest(uuid, body),
  );

export const useDeriveHolders = (uuid: Uuid) =>
  useRequestAction<RightsHolder[], void>(uuid, () => api.deriveHolders(uuid));
export const useAddHolder = (uuid: Uuid) =>
  useRequestAction<RightsHolder, api.HolderInput>(uuid, (body) => api.addHolder(uuid, body));
export const useConfirmHolder = (uuid: Uuid) =>
  useRequestAction<
    RightsHolder,
    { holderUuid: Uuid; responder_name?: string | null; responder_contact?: string | null }
  >(uuid, ({ holderUuid, ...body }) => api.confirmHolder(uuid, holderUuid, body));
export const useIssueTickets = (uuid: Uuid) =>
  useRequestAction<RightsHolder[], Parameters<typeof api.issueTickets>[1]>(uuid, (body) =>
    api.issueTickets(uuid, body),
  );
export const useReturnTicket = (uuid: Uuid) =>
  useRequestAction<RightsHolder, { holderUuid: Uuid; summary: string; evidence: File | null }>(
    uuid,
    ({ holderUuid, ...input }) => api.returnTicket(uuid, holderUuid, input),
  );
export const useEscalateTicket = (uuid: Uuid) =>
  useRequestAction<RightsHolder, Uuid>(uuid, (holderUuid) => api.escalateTicket(uuid, holderUuid));

export const useDeriveScope = (uuid: Uuid) =>
  useRequestAction<RightsScopeItem[], void>(uuid, () => api.deriveScope(uuid));
export const useDecideItem = (uuid: Uuid) =>
  useRequestAction<RightsScopeItem, { itemUuid: Uuid } & api.DecideItemInput>(
    uuid,
    ({ itemUuid, ...body }) => api.decideItem(uuid, itemUuid, body),
  );
export const useApplyItem = (uuid: Uuid) =>
  useRequestAction<RightsScopeItem, Uuid>(uuid, (itemUuid) => api.applyItem(uuid, itemUuid));

export const useRespond = (uuid: Uuid) =>
  useRequestAction<RightsRequest, Parameters<typeof api.respond>[1]>(uuid, (body) =>
    api.respond(uuid, body),
  );
export const useDecideGrievance = (uuid: Uuid) =>
  useRequestAction<GrievanceDecisionResult, api.GrievanceDecisionInput>(uuid, (body) =>
    api.decideGrievance(uuid, body),
  );

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
