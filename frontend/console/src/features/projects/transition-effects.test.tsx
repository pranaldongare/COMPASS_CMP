/**
 * A transition refreshes every view it can change (review 2026-10-01, ARCH-3).
 *
 * Approving a project can publish its notice. The transition hook invalidated
 * the project, the project list and the dashboard - and not the notice's own
 * detail, the cross-project notice list or the copy-source list, so a DPO who
 * approved a project and opened its notice saw it still as a draft until a
 * reload. Each test here caches every affected view first, then transitions,
 * then asks which of them are now stale.
 */
import { QueryClient } from "@tanstack/react-query";
import { act, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useCloseProject, useTransition } from "@/features/projects/mutations";
import { keys } from "@/lib/query";
import { API, HttpResponse, http, server } from "@/test/server";
import { renderHook } from "@/test/render";

const PROJECT = "0b7c1d2e-1111-4222-8333-444455556666";
const NOTICE = "9a8b7c6d-1111-4222-8333-444455556666";

/** Every view an approval can change, cached as if the DPO had visited it. */
const AFFECTED = [
  keys.project.detail(PROJECT),
  keys.project.transitions(PROJECT),
  keys.project.list(),
  keys.project.allApprovals(),
  keys.dashboard.all,
  keys.notice.list(PROJECT),
  keys.notice.detail(NOTICE),
  keys.notice.checklist(NOTICE),
  keys.notice.all(),
  keys.notice.all({ status: "published" }),
  keys.notice.copySources,
];

function cachedClient(): QueryClient {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity, staleTime: Infinity } },
  });
  for (const key of AFFECTED) qc.setQueryData(key, { cached: true });
  return qc;
}

function stale(qc: QueryClient): string[] {
  return AFFECTED.filter((key) => !qc.getQueryState(key)?.isInvalidated).map((key) =>
    JSON.stringify(key),
  );
}

describe("a project transition", () => {
  it("leaves no view it could have changed fresh", async () => {
    server.use(
      http.post(`${API}/projects/${PROJECT}/transition`, () =>
        HttpResponse.json({ status: "approved", published_notice_uuid: NOTICE }),
      ),
    );
    const qc = cachedClient();
    const { result } = renderHook(() => useTransition(PROJECT), { queryClient: qc });

    await act(() => result.current.mutateAsync({ to_status: "approved" } as never));

    await waitFor(() => expect(stale(qc)).toEqual([]));
  });
});

describe("closing a project", () => {
  it("refreshes the same views a transition does", async () => {
    server.use(
      http.post(`${API}/projects/${PROJECT}/close`, () =>
        HttpResponse.json({ ok: true, message: "Closed." }),
      ),
    );
    const qc = cachedClient();
    const { result } = renderHook(() => useCloseProject(PROJECT), { queryClient: qc });

    await act(() => result.current.mutateAsync({}));

    await waitFor(() => expect(stale(qc)).toEqual([]));
  });
});
