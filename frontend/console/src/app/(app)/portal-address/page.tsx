/**
 * Portal address (0072): the address every link to the data principal's
 * portal starts with - a consent link copied here, the public link for
 * reporting a breach, the links in the platform's mail.
 *
 * It was a setting in two files, read when a service starts. A deployment
 * with no domain name yet is reached at an IP that changes, so it is the
 * administrator's to set here, and takes effect without a restart. Left
 * empty, the configured address is used.
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
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import {
  getPortalAddress,
  isPortalAddress,
  portalAddressKey,
  savePortalAddress,
  setPortalUrl,
  type PortalAddress,
} from "@/features/portal-address";
import { isApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import { useToast } from "@/providers";

const SHAPE =
  "Enter the address as http:// or https:// and a host, with a port if it has one, and nothing after it.";

function AddressForm({ saved }: { saved: PortalAddress }) {
  const toast = useToast();
  const client = useQueryClient();
  const [address, setAddress] = React.useState(saved.portal_url ?? "");
  const [problem, setProblem] = React.useState<string | null>(null);

  const save = useMutation({
    mutationFn: savePortalAddress,
    onSuccess: (now) => {
      client.setQueryData(portalAddressKey, now);
      setAddress(now.portal_url ?? "");
      setProblem(null);
      // This tab copies with the new address at once; the others when they
      // next ask who is signed in.
      setPortalUrl(now.in_use);
      void client.invalidateQueries({ queryKey: keys.auth.me });
      void client.invalidateQueries({ queryKey: keys.breach.settings() });
      toast.success(
        "Portal address saved",
        now.portal_url ? `Links now start with ${now.in_use}.` : "Links start with the configured address.",
      );
    },
    onError: (err) =>
      setProblem(isApiError(err) ? err.userMessage() : "Not saved. Try again in a moment."),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const typed = address.trim();
    if (typed && !isPortalAddress(typed)) {
      setProblem(SHAPE);
      return;
    }
    save.mutate(typed || null);
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-5" noValidate>
      {problem && <Alert tone="danger">{problem}</Alert>}
      <Field
        label="Portal address"
        hint="For example http://10.20.30.40:3001, or https://portal.example.org once there is a domain name. No path after it. Leave it empty to use the configured address."
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
            placeholder={saved.configured_url}
          />
        )}
      </Field>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant="primary" loading={save.isPending}>
          Save
        </Button>
        {saved.portal_url && (
          <Button
            type="button"
            variant="secondary"
            disabled={save.isPending}
            onClick={() => save.mutate(null)}
          >
            Use the configured address
          </Button>
        )}
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

export default function PortalAddressPage() {
  const query = useQuery({ queryKey: portalAddressKey, queryFn: getPortalAddress });
  return (
    <>
      <PageHeader
        title="Portal address"
        description="The address every link to the data principal's portal starts with. Kept by the administrator."
      />
      {query.isLoading && <Skeleton className="h-64" />}
      {query.error && (
        <Alert tone="danger" title="Could not load the address">
          {query.error.message}
        </Alert>
      )}
      {query.data && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>In use now</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                Consent links copied in the console, the public link for reporting a breach, and
                the links in mail to data principals all start with this. A change takes effect
                within a few seconds, with nothing restarted. Links already handed out keep the
                address they were copied with.
              </p>
            </CardHeader>
            <CardBody className="space-y-2 text-sm">
              <p>
                <Mono className="break-all">{query.data.in_use}</Mono>
              </p>
              <p className="text-xs text-text-muted">
                {query.data.portal_url
                  ? "Set here. The configured address is "
                  : "This is the configured address, used while none is set here: "}
                <Mono>{query.data.configured_url}</Mono>
              </p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Set the address</CardTitle>
            </CardHeader>
            <CardBody>
              <AddressForm saved={query.data} />
            </CardBody>
          </Card>
        </div>
      )}
    </>
  );
}
