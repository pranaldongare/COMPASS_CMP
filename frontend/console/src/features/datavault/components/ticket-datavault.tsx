/**
 * On a DCO Admin's own ticket: the assets DataVault listed for the project
 * they answer for (0070), so they know what to act on without going to look.
 * Nothing for any other ticket, or before DataVault has answered.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { datavaultKeys, getTicketDataVault } from "@/features/datavault/api";
import { AssetTable } from "@/features/datavault/components/asset-table";
import { formatDateTime } from "@/lib/format";
import type { Uuid } from "@/types";

export function TicketDataVault({ holderUuid }: { holderUuid: Uuid }) {
  const found = useQuery({
    queryKey: datavaultKeys.ticket(holderUuid),
    queryFn: () => getTicketDataVault(holderUuid),
    retry: false,
  });
  const d = found.data;
  if (!d || !d.asked_at) return null;
  return (
    <details open>
      <summary className="cursor-pointer text-xs font-medium tracking-wider text-text-subtle uppercase">
        Held in DataVault for this project
      </summary>
      <div className="mt-2 space-y-2">
        <p className="text-xs text-text-muted">
          As DataVault listed them on {formatDateTime(d.asked_at)}.
        </p>
        {d.assets.length === 0 ? (
          <p className="text-sm">DataVault listed nothing for this project.</p>
        ) : (
          <AssetTable assets={d.assets} links={false} />
        )}
      </div>
    </details>
  );
}
