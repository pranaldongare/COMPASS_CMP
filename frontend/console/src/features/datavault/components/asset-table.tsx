/**
 * The assets DataVault listed, as a table: the asset, the consent and the
 * project it named - ours where they matched, as sent where they did not -
 * its mid, and where it is kept. On an erasure request (0071), where each
 * stands in DataVault too: not sent, left out because the request does not
 * reach it, or what DataVault last said of it.
 */
import Link from "next/link";

import { Badge, Mono, Table, Td, Th, Tr } from "@/components/ui/primitives";
import type { DataVaultAsset } from "@/features/datavault/api";
import { formatDateTime } from "@/lib/format";

/** Ours by its number or name - a link where the reader may open it - else
 *  what DataVault sent, marked as not found here. */
function Named({
  href,
  label,
  sent,
}: {
  href: string | null;
  label: string | null;
  sent: string | null;
}) {
  if (label) {
    return href ? (
      <Link href={href} className="text-accent-text hover:underline">
        {label}
      </Link>
    ) : (
      <span>{label}</span>
    );
  }
  if (!sent) return <span className="text-text-subtle">Not given</span>;
  return (
    <span>
      <Mono className="break-all">{sent}</Mono>
      <span className="block text-xs text-text-subtle">
        Not found among this person&apos;s records
      </span>
    </span>
  );
}

/** Where one asset stands in DataVault on an erasure request. Colour never
 *  carries it alone: the words are always there. */
export function ErasureStatus({ asset: a }: { asset: DataVaultAsset }) {
  if (!a.in_scope)
    return (
      <span className="text-xs text-text-subtle">
        Left out: this request does not reach it
      </span>
    );
  switch (a.erasure_status) {
    case null:
      return <span className="text-xs text-text-subtle">Not sent</span>;
    case "unanswered":
      return (
        <Badge tone="warning" dot>
          Sent, no answer yet
        </Badge>
      );
    case "pending":
      return (
        <Badge tone="info" dot>
          Pending
        </Badge>
      );
    case "erased":
      return (
        <span>
          <Badge tone="success" dot>
            Erased
          </Badge>
          {a.erasure_completed_at && (
            <span className="block text-xs text-text-muted">
              {formatDateTime(a.erasure_completed_at)}
            </span>
          )}
        </span>
      );
    case "failed":
      return (
        <span>
          <Badge tone="danger" dot>
            Not erased
          </Badge>
          {a.erasure_reason && (
            <span className="block text-xs text-text-muted">{a.erasure_reason}</span>
          )}
        </span>
      );
    case "not_held":
      return (
        <Badge tone="neutral" dot>
          Not held
        </Badge>
      );
  }
}

export function AssetTable({
  assets,
  links = true,
  erasure = false,
}: {
  assets: DataVaultAsset[];
  links?: boolean;
  /** An erasure request: show where each asset stands in DataVault. */
  erasure?: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <thead>
          <Tr>
            <Th>Asset</Th>
            <Th>Consent</Th>
            <Th>Project</Th>
            <Th>MID</Th>
            <Th>Data path</Th>
            {erasure && <Th>Erasure</Th>}
          </Tr>
        </thead>
        <tbody>
          {assets.map((a, i) => (
            <Tr key={`${a.asset_ref}-${i}`}>
              <Td className="whitespace-nowrap">
                <Mono>{a.asset_ref}</Mono>
              </Td>
              <Td>
                <Named
                  href={links && a.consent_uuid ? `/consents/${a.consent_uuid}` : null}
                  label={a.consent_no !== null ? `Consent ID ${a.consent_no}` : null}
                  sent={a.consent_ref}
                />
              </Td>
              <Td>
                <Named
                  href={links && a.project_uuid ? `/projects/${a.project_uuid}` : null}
                  label={
                    a.project_name ??
                    (a.project_no !== null ? `Project ID ${a.project_no}` : null)
                  }
                  sent={a.project_ref}
                />
              </Td>
              <Td>{a.mid ?? <span className="text-text-subtle">Not given</span>}</Td>
              <Td>
                {a.datapath ? (
                  <Mono className="break-all">{a.datapath}</Mono>
                ) : (
                  <span className="text-text-subtle">Not given</span>
                )}
              </Td>
              {erasure && (
                <Td>
                  <ErasureStatus asset={a} />
                </Td>
              )}
            </Tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
