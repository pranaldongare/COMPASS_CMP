/**
 * Data source registry.
 *
 * `is_authoritative_for` is the column doing real work. It lists the data
 * elements this source owns. Without it a nightly identity sync will overwrite a
 * value that was corrected under a rights request, and nobody will notice - the
 * correction simply stops being true overnight.
 */
"use client";

import { Ban, Building2, Eye, Pencil, Plus, UserRoundCog } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  FilterBar,
  FilterSelect,
  FilterToggle,
  ResourceList,
  SearchBox,
  useCursorStack,
  useFilterParam,
} from "@/components/data-display/resource-list";
import { SourceForm } from "@/features/registry/components/forms";
import {
  AssignSourceOwnerDialog,
  SourceOwner,
} from "@/features/registry/components/source-owner";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { RowActions, Tooltip } from "@/components/ui/overlay";
import { EmptyRecords } from "@/components/ui/graphics";
import { Alert, Badge, Button, Td, Tr } from "@/components/ui/primitives";
import { StatusBadge } from "@/components/ui/status";
import { useEnums } from "@/features/meta";
import {
  useAllProcessors,
  useProcessors,
  useSources,
  useSuspendSource,
} from "@/features/registry";
import type { DataSource } from "@/types";
import { humanise } from "@/lib/format";
import { useAuth, useToast } from "@/providers";

export default function SourcesPage() {
  const { me } = useAuth();
  const toast = useToast();
  const stack = useCursorStack();

  // In the URL. A dashboard count is a claim about a subset — "12 sources
  // with nobody accountable" — and a link that lands on the unfiltered
  // registry makes the reader find those twelve themselves; and a filter kept
  // only on the page was lost on reload or on Back from a source (UX-5).
  const [status, setStatus] = useFilterParam("status");
  const [q, setQ] = useFilterParam("q");
  // Narrowed to one processor's sources (2026-10-09).
  const [processor, setProcessor] = useFilterParam("processor");
  // A DCO or an RCO sees the sources of the processors they collect for and
  // no others (0050); the server applies it, and the page says so.
  const collector = me?.role === "dco" || me?.role === "rco";
  const allProcessors = useAllProcessors();
  const mine = useProcessors(collector ? { mine: true, limit: 100 } : { limit: 1 });
  const processorOptions = collector ? (mine.data?.items ?? []) : (allProcessors.data ?? []);
  const collectsForNone = collector && mine.isSuccess && mine.data.items.length === 0;
  const [unmappedFlag, setUnmappedFlag] = useFilterParam("unmapped");
  const [unownedFlag, setUnownedFlag] = useFilterParam("unowned");
  const unmapped = unmappedFlag === "1";
  const unowned = unownedFlag === "1";
  const setUnmapped = (on: boolean) => setUnmappedFlag(on ? "1" : "");
  const setUnowned = (on: boolean) => setUnownedFlag(on ? "1" : "");
  const [creating, setCreating] = React.useState(false);
  const [editing, setEditing] = React.useState<DataSource | null>(null);
  const [assigning, setAssigning] = React.useState<DataSource | null>(null);
  const suspend = useSuspendSource();

  const { data: enums } = useEnums();
  // No cast: `useSources` is typed `Page<DataSource>`. The `as unknown as`
  // that stood here predated that and would have hidden a real drift.
  const query = useSources({
    status: status || undefined,
    q: q || undefined,
    processor: processor || undefined,
    unmapped: unmapped || undefined,
    unowned: unowned || undefined,
    cursor: stack.cursor,
    limit: 25,
  });

  const canSuspend = me?.role === "dpo" || me?.role === "admin";
  // Making somebody accountable is the DCO Admin's routing step as well as an
  // administrative one, so they hold it alongside the DPO and the administrator.
  const canAssignOwner = canSuspend || me?.role === "dco_admin";
  // A collection owner registers the rigs they will run: a campus lead who
  // needs a second one should not have to ask somebody else to type it in.
  // Which processor they may register under is the constraint, and the form
  // applies it — not whether they may at all.
  const canCreate =
    canSuspend || me?.role === "dco_admin" || (collector && !collectsForNone);

  async function onSuspend(uuid: string, name: string) {
    try {
      await suspend.mutateAsync(uuid);
      toast.success("Source suspended", `Imports from ${name} are now refused.`);
    } catch (err) {
      const message =
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "Could not suspend the source.";
      toast.error("Suspension failed", message);
    }
  }

  return (
    <>
      <PageHeader
        title="Data sources"
        description="Where records come from and which fields each one owns. A source that is not authoritative for a field must never overwrite it."
        actions={
          canCreate ? (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus className="size-4" />
              Register source
            </Button>
          ) : null
        }
      />

      {collector &&
        (collectsForNone ? (
          <Alert tone="warning" className="mb-4" title="You collect for no processor yet">
            You see the data sources of the processors you collect for, and none is assigned to
            you. Ask the administrator to add them on your account.
          </Alert>
        ) : mine.data?.items.length ? (
          <p className="mb-4 text-sm text-text-muted">
            The data sources of the processors you collect for:{" "}
            {mine.data.items.map((p) => p.legal_name).join(", ")}. New sources are registered
            under these.
          </p>
        ) : null)}

      <FilterBar>
        <SearchBox
          value={q}
          placeholder="Name or code"
          onSubmit={(term) => {
            setQ(term);
            stack.reset();
          }}
        />
        <FilterSelect
          label="Processor"
          value={processor}
          onChange={(v) => {
            setProcessor(v);
            stack.reset();
          }}
          options={processorOptions.map((p) => ({ value: p.processor_uuid, label: p.legal_name }))}
          allLabel="All processors"
        />
        <FilterSelect
          label="Status"
          value={status}
          onChange={(v) => {
            setStatus(v);
            stack.reset();
          }}
          options={enums?.record_status ?? []}
          allLabel="All statuses"
        />

        {/* The gap, as a filter rather than a constraint.
            "No processor named" is a legitimate state for a source the
            organisation runs itself, and an error for one a third party
            operates - and only a person can tell those apart. So the system
            makes the set reviewable instead of guessing. */}
        {/* Never theirs to see: a source with no processor is no processor's. */}
        {!collector && (
          <FilterToggle
            label="No processor named"
            checked={unmapped}
            onChange={(on) => {
              setUnmapped(on);
              stack.reset();
            }}
          />
        )}

        {/* The routing queue, as a filter. A source nobody is accountable for
            cannot route a project, so this is the list somebody works through
            rather than a fault to fix. */}
        <FilterToggle
          label="Nobody accountable"
          checked={unowned}
          onChange={(on) => {
            setUnowned(on);
            stack.reset();
          }}
        />
      </FilterBar>

      <ResourceList<DataSource>
        query={query}
        stack={stack}
        caption="Registered data sources"
        columns={["Source", "Processor", "Accountable", "Authoritative for", "Status", ""]}
        keyOf={(s) => s.source_uuid}
        empty={{
          illustration: <EmptyRecords />,
          title: status || q || processor ? "No sources match" : "No data sources registered",
          description: "An import must name the source the manifest came from.",
        }}
        // Six columns, one line each, one menu (2026-10-10): role and exchange
        // ride under the name, long names are cut with the whole in a
        // tooltip, and View / Reassign / Edit / Suspend live in the ⋯ menu.
        row={(s) => (
          <Tr>
            <Td className="max-w-72">
              <Link
                href={`/sources/${s.source_uuid}`}
                className="block truncate font-medium text-text hover:text-accent-text hover:underline"
                title={s.name}
              >
                {s.name}
              </Link>
              <p className="mt-0.5 truncate text-xs text-text-subtle">
                <span className="font-mono">{s.source_code}</span>
                {" · "}
                {humanise(s.source_role)} · {humanise(s.exchange_mode)}
              </p>
            </Td>
            {/* Who operates this source. Optional by design: a source the
                organisation runs itself has no processor, and requiring one
                would mean inventing a processor record for yourself. But an
                absent one is worth *seeing* - a third-party source with no
                named operator is an s.8(2) contract nobody can point to. */}
            <Td className="max-w-60">
              {s.processor_name && s.processor_uuid ? (
                <Link
                  href={`/processors/${s.processor_uuid}`}
                  className="block truncate text-text-muted hover:text-text hover:underline"
                  title={s.processor_name}
                >
                  {s.processor_name}
                </Link>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs text-text-subtle">
                  <Building2 className="size-3.5" aria-hidden="true" />
                  first party
                </span>
              )}
            </Td>
            <Td className="whitespace-nowrap">
              <SourceOwner source={s} />
            </Td>
            <Td>
              {s.is_authoritative_for.length === 0 ? (
                <span className="text-xs text-text-subtle">nothing</span>
              ) : (
                <Tooltip content={s.is_authoritative_for.map(humanise).join(", ")}>
                  <span className="inline-flex items-center gap-1 whitespace-nowrap">
                    <Badge tone="neutral" dot={false}>
                      {humanise(s.is_authoritative_for[0])}
                    </Badge>
                    {s.is_authoritative_for.length > 1 && (
                      <span className="text-xs text-text-subtle">
                        +{s.is_authoritative_for.length - 1}
                      </span>
                    )}
                  </span>
                </Tooltip>
              )}
            </Td>
            <Td>
              <StatusBadge kind="record" value={s.status} />
            </Td>
            <Td className="w-12 text-right">
              <RowActions
                label={`Actions for ${s.name}`}
                actions={[
                  { label: "View", icon: Eye, href: `/sources/${s.source_uuid}` },
                  ...(canAssignOwner && s.status === "active"
                    ? [
                        {
                          label: s.owner_name ? "Reassign" : "Assign",
                          icon: UserRoundCog,
                          onSelect: () => setAssigning(s),
                        },
                      ]
                    : []),
                  ...(canSuspend
                    ? [{ label: "Edit", icon: Pencil, onSelect: () => setEditing(s) }]
                    : []),
                  ...(canSuspend && s.status === "active"
                    ? [
                        {
                          label: "Suspend",
                          icon: Ban,
                          destructive: true,
                          disabled: suspend.isPending,
                          onSelect: () => onSuspend(s.source_uuid, s.name),
                        },
                      ]
                    : []),
                ]}
              />
            </Td>
          </Tr>
        )}
      />

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent
          title="Register a data source"
          description="Declare which fields it owns — anything else it sends must never overwrite ours."
          size="lg"
        >
          <SourceForm onDone={() => setCreating(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(editing)} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent title="Edit data source" size="lg">
          {editing && <SourceForm source={editing} onDone={() => setEditing(null)} />}
        </DialogContent>
      </Dialog>

      <AssignSourceOwnerDialog source={assigning} onClose={() => setAssigning(null)} />
    </>
  );
}
