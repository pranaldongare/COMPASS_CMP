/**
 * Invalidation by what happened, not by which hook happened to do it.
 *
 * A write's consequences are the server's, and they cross features: approving
 * a project publishes its notice, so the notice's detail, the cross-project
 * notice list and the list notices are copied from are all stale the moment
 * the project moves. When each hook listed its own keys, the project hooks
 * listed project keys, and a DPO who approved a project and opened its notice
 * saw a draft until she reloaded (review 2026-10-01, ARCH-3).
 *
 * So the consequence is named once, here, and every hook that causes it calls
 * the same function. Broad on purpose: one extra refetch is cheap, a screen
 * that contradicts what the person just did is not.
 */
import type { QueryClient, QueryKey } from "@tanstack/react-query";

import { keys, prefixes } from "@/lib/query/keys";
import type { Uuid } from "@/types";

function invalidate(qc: QueryClient, queryKeys: readonly QueryKey[]): void {
  for (const queryKey of queryKeys) void qc.invalidateQueries({ queryKey });
}

/** Every notice view: one notice's pages, every list of them, the copy sources. */
const NOTICES: readonly QueryKey[] = [prefixes.anyNotice, prefixes.anyNoticeList];

export const effects = {
  /**
   * Some notice changed - its words, its purposes, its status.
   *
   * Its project's page counts its notice's readiness, so the project goes too.
   */
  noticesChanged(qc: QueryClient, projectUuid?: Uuid): void {
    invalidate(qc, [...NOTICES, ...(projectUuid ? [keys.project.detail(projectUuid)] : [])]);
  },

  /**
   * A project moved through its lifecycle, or closed.
   *
   * Everything under the project, every project list, the approval queue,
   * the dashboard's counts - and every notice view, because approval
   * publishes the project's notice and closing retires it.
   */
  projectMoved(qc: QueryClient, projectUuid: Uuid): void {
    invalidate(qc, [
      keys.project.detail(projectUuid),
      keys.project.list(),
      prefixes.anyApprovalList,
      keys.dashboard.all,
      ...NOTICES,
    ]);
  },
} as const;
