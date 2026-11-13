/**
 * The assets DataVault listed, as a table: the asset, the consent and the
 * project it named - ours where they matched, as sent where they did not -
 * its mid, and where it is kept.
 */
import Link from "next/link";

import { Mono, Table, Td, Th, Tr } from "@/components/ui/primitives";
import type { DataVaultAsset } from "@/features/datavault/api";

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

export function AssetTable({
  assets,
  links = true,
}: {
  assets: DataVaultAsset[];
  links?: boolean;
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
            </Tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
