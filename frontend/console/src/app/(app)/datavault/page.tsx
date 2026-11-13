/**
 * DataVault connection (0070): where the platform reaches DataVault.
 *
 * The administrator's page. The address could not be written into the code,
 * so it is set here with the key DataVault asks for. The key is stored
 * encrypted and never shown again: the page says only that one is set, and
 * a new one replaces it. Switched off, the platform calls nothing and a
 * rights request says DataVault is not set up.
 *
 * What is sent on a check: the request's reference and the person's Person
 * ID, as `GET {address}/lookup?request_id=..&person_id=..`.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Skeleton,
} from "@/components/ui/primitives";
import {
  datavaultKeys,
  getConnection,
  saveConnection,
  type DataVaultConnection,
} from "@/features/datavault/api";
import { formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";

function said(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

function ConnectionForm({ saved }: { saved: DataVaultConnection }) {
  const toast = useToast();
  const client = useQueryClient();
  const [address, setAddress] = React.useState(saved.base_url ?? "");
  const [header, setHeader] = React.useState(saved.api_key_header);
  const [key, setKey] = React.useState("");
  const [removeKey, setRemoveKey] = React.useState(false);
  const [enabled, setEnabled] = React.useState(saved.enabled);
  const [problem, setProblem] = React.useState<string | null>(null);

  const save = useMutation({
    mutationFn: saveConnection,
    onSuccess: (now) => {
      client.setQueryData(datavaultKeys.connection, now);
      setKey("");
      setRemoveKey(false);
      setAddress(now.base_url ?? "");
      setHeader(now.api_key_header);
      setEnabled(now.enabled);
      setProblem(null);
      toast.success(
        "DataVault connection saved",
        now.enabled ? "Switched on." : "Switched off: nothing is called.",
      );
    },
    onError: (err) => setProblem(said(err, "Not saved. Try again in a moment.")),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (enabled && !address.trim()) {
      setProblem("Enter DataVault's address before switching it on.");
      return;
    }
    save.mutate({
      base_url: address.trim() || null,
      api_key_header: header.trim() || "X-API-Key",
      enabled,
      ...(key.trim() ? { api_key: key.trim() } : removeKey ? { clear_api_key: true } : {}),
    });
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-5" noValidate>
      <Field
        label="DataVault address"
        hint="For example https://datavault.example.internal/api. The platform adds /lookup to it."
      >
        {(props) => (
          <Input
            {...props}
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="https://"
          />
        )}
      </Field>
      <Field
        label="API key"
        hint={
          saved.api_key_set
            ? "A key is stored. It is not shown again; type a new one to replace it."
            : "No key is stored. Leave this empty if DataVault asks for none."
        }
      >
        {(props) => (
          <Input
            {...props}
            type="password"
            autoComplete="new-password"
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              if (e.target.value) setRemoveKey(false);
            }}
            placeholder={saved.api_key_set ? "Stored" : ""}
          />
        )}
      </Field>
      {saved.api_key_set && !key && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={removeKey}
            onChange={(e) => setRemoveKey(e.target.checked)}
          />
          Remove the stored key
        </label>
      )}
      <Field
        label="Header the key is sent in"
        hint="X-API-Key unless DataVault's team named another."
      >
        {(props) => (
          <Input
            {...props}
            autoComplete="off"
            spellCheck={false}
            value={header}
            onChange={(e) => setHeader(e.target.value)}
          />
        )}
      </Field>
      <div className="flex items-start gap-2 text-sm">
        <input
          id="datavault-enabled"
          type="checkbox"
          className="mt-0.5"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          aria-describedby="datavault-enabled-hint"
        />
        <div>
          <label htmlFor="datavault-enabled" className="font-medium">
            Switched on
          </label>
          <p id="datavault-enabled-hint" className="text-xs text-text-muted">
            Off: the platform calls nothing, and a rights request says DataVault is not set
            up.
          </p>
        </div>
      </div>
      {problem && <Alert tone="danger">{problem}</Alert>}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save"}
        </Button>
        {saved.updated_at && (
          <span className="text-xs text-text-muted">
            Last changed {formatDateTime(saved.updated_at)}
            {saved.updated_by_name ? ` by ${saved.updated_by_name}` : ""}
          </span>
        )}
      </div>
    </form>
  );
}

export default function DataVaultConnectionPage() {
  const found = useQuery({ queryKey: datavaultKeys.connection, queryFn: getConnection });
  return (
    <>
      <PageHeader
        title="DataVault connection"
        description="Where the platform asks DataVault what it holds of a person, for a rights request."
      />
      <div className="max-w-2xl space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              On a check the platform sends the request&apos;s reference and the
              person&apos;s Person ID, and nothing else. Every check, and every change made
              here, is on the audit trail.
            </p>
          </CardHeader>
          <CardBody>
            {found.isLoading ? (
              <Skeleton className="h-64" />
            ) : found.error || !found.data ? (
              <Alert tone="danger">
                {said(found.error, "The connection could not be loaded.")}
              </Alert>
            ) : (
              <ConnectionForm saved={found.data} />
            )}
          </CardBody>
        </Card>
      </div>
    </>
  );
}
