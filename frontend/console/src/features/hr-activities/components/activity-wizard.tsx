/**
 * Creating an HR activity (ADR 0033): category, then the approved version,
 * then the purposes - the mandatory ones chosen and locked - then the name
 * and the one description, then who signs in through the link and until
 * when. Create makes the whole activity live in one request and shows its
 * link once, with Copy.
 */
"use client";

import { Check, Lock } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { DialogFooter } from "@/components/ui/dialog";
import { Alert, Button, Field, Input, Mono, Select, Skeleton, Textarea } from "@/components/ui/primitives";
import { CopyLinkButton } from "@/features/consent/components/copy-link";
import { useCreateHrActivity } from "@/features/hr-activities/mutations";
import { useActivityOptions } from "@/features/hr-activities/queries";
import { useToast } from "@/providers";
import type { ActivityOptionVersion, HrActivityCreated } from "@/types";

const STEPS = ["What", "Purposes", "Description", "Link"] as const;

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

function inAMonth(): string {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().slice(0, 10);
}

/** The purposes an activity carries from a version: the mandatory ones
 *  always, the rest as chosen, in the version's order. */
export function PurposePicker({
  version,
  chosen,
  onChange,
}: {
  version: ActivityOptionVersion;
  chosen: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <fieldset className="space-y-1.5">
      <legend className="mb-2 text-sm text-text-muted">
        A purpose marked with a lock is mandatory on this version and is always included.
      </legend>
      {version.purposes.map((p) => {
        const on = p.is_mandatory || chosen.includes(p.purpose_uuid);
        return (
          <label
            key={p.purpose_uuid}
            className="flex cursor-pointer items-center gap-2 rounded-lg border border-border px-2.5 py-2 text-sm has-[:checked]:border-accent-border has-[:checked]:bg-accent-subtle"
          >
            <input
              type="checkbox"
              checked={on}
              disabled={p.is_mandatory}
              onChange={() =>
                onChange(
                  on
                    ? chosen.filter((u) => u !== p.purpose_uuid)
                    : [...chosen, p.purpose_uuid],
                )
              }
              className="size-4 rounded border-border-strong accent-[var(--accent)]"
            />
            <span className="flex-1">{p.name}</span>
            {p.is_mandatory && (
              <span className="flex items-center gap-1 text-2xs text-text-muted">
                <Lock className="size-3" aria-hidden="true" />
                mandatory
              </span>
            )}
          </label>
        );
      })}
    </fieldset>
  );
}

export function ActivityWizard({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const router = useRouter();
  const options = useActivityOptions();
  const create = useCreateHrActivity();
  const [step, setStep] = React.useState(0);
  const [categoryUuid, setCategoryUuid] = React.useState("");
  const [versionUuid, setVersionUuid] = React.useState("");
  const [chosen, setChosen] = React.useState<string[]>([]);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [audience, setAudience] = React.useState<"sso" | "otp">("sso");
  const [expires, setExpires] = React.useState(inAMonth);
  const [error, setError] = React.useState<string | null>(null);
  const [made, setMade] = React.useState<HrActivityCreated | null>(null);

  const categories = options.data ?? [];
  const category = categories.find((c) => c.category_uuid === categoryUuid);
  const version = category?.versions.find((v) => v.version_uuid === versionUuid);
  const purposeUuids = version
    ? version.purposes
        .filter((p) => p.is_mandatory || chosen.includes(p.purpose_uuid))
        .map((p) => p.purpose_uuid)
    : [];
  const tooLong = version ? description.trim().length > version.slot_max_length : false;

  const ready = [
    Boolean(version),
    purposeUuids.length > 0,
    Boolean(name.trim()) && Boolean(description.trim()) && !tooLong,
    Boolean(expires),
  ];

  async function submit() {
    if (!version || !category) return;
    setError(null);
    try {
      setMade(
        await create.mutateAsync({
          category_uuid: category.category_uuid,
          template_version_uuid: version.version_uuid,
          purpose_uuids: purposeUuids,
          name: name.trim(),
          description: description.trim(),
          audience_mode: audience,
          link_expires_at: new Date(`${expires}T23:59:59`).toISOString(),
        }),
      );
      toast.success("Activity created", "It is live. Share its link.");
    } catch (err) {
      setError(messageOf(err, "Could not create the activity."));
    }
  }

  if (options.isLoading) return <Skeleton className="h-48" />;
  if (options.error) return <Alert tone="danger">{options.error.userMessage()}</Alert>;

  if (made) {
    return (
      <div className="space-y-4">
        <Alert tone="success" title="The activity is live">
          <p className="text-sm">
            Share this link with the people taking part.{" "}
            {made.audience_mode === "sso"
              ? "They sign in with their organisation account."
              : "They sign in with a one-time code."}{" "}
            It can be read back from the activity&apos;s page.
          </p>
        </Alert>
        <div className="flex items-center gap-2 rounded-md border border-border p-2">
          <Mono className="min-w-0 flex-1 truncate text-xs">{made.url_path}</Mono>
          <CopyLinkButton link={{ url_path: made.url_path, status: "active" }} />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onDone}>
            Close
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              onDone();
              router.push(`/hr-activities/${made.activity_uuid}`);
            }}
          >
            Open the activity
          </Button>
        </DialogFooter>
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <Alert tone="info" title="Nothing to make an activity from yet">
        <p className="text-sm">
          You are assigned to no active category, or none has an approved template version. The
          administrator assigns categories; Legal approves the versions.
        </p>
      </Alert>
    );
  }

  return (
    <div className="space-y-5">
      <ol className="flex flex-wrap gap-2 text-xs" aria-label="Steps">
        {STEPS.map((label, i) => (
          <li
            key={label}
            aria-current={i === step ? "step" : undefined}
            className={
              i === step
                ? "rounded-full bg-accent-subtle px-2.5 py-1 font-semibold text-accent-text"
                : "rounded-full px-2.5 py-1 text-text-muted"
            }
          >
            {i < step && <Check className="mr-1 inline size-3" aria-hidden="true" />}
            {i + 1}. {label}
          </li>
        ))}
      </ol>

      {error && <Alert tone="danger">{error}</Alert>}

      {step === 0 && (
        <div className="space-y-4">
          <Field label="Category" required>
            {(p) => (
              <Select
                {...p}
                value={categoryUuid}
                onChange={(e) => {
                  setCategoryUuid(e.target.value);
                  setVersionUuid("");
                  setChosen([]);
                }}
              >
                <option value="">Choose a category</option>
                {categories.map((c) => (
                  <option key={c.category_uuid} value={c.category_uuid}>
                    {c.category_code} · {c.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          {category && (
            <Field
              label="Template version"
              hint="The legal text Legal approved. The activity keeps it until you upgrade it."
              required
            >
              {(p) => (
                <Select
                  {...p}
                  value={versionUuid}
                  onChange={(e) => {
                    setVersionUuid(e.target.value);
                    setChosen([]);
                  }}
                >
                  <option value="">
                    {category.versions.length ? "Choose a version" : "No approved version yet"}
                  </option>
                  {category.versions.map((v) => (
                    <option key={v.version_uuid} value={v.version_uuid}>
                      {v.template_code} · {v.template_title} · v{v.version}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          )}
        </div>
      )}

      {step === 1 && version && (
        <PurposePicker version={version} chosen={chosen} onChange={setChosen} />
      )}

      {step === 2 && version && (
        <div className="space-y-4">
          <Field label="Activity name" hint="Shown on the notice and in your registers." required>
            {(p) => (
              <Input
                {...p}
                value={name}
                maxLength={200}
                placeholder="Wellness week, Pune"
                onChange={(e) => setName(e.target.value)}
              />
            )}
          </Field>
          <Field
            label="Description"
            hint={
              version.slot_guidance ??
              "What the activity is, who runs it and when. No links; Legal's text carries those."
            }
            error={
              tooLong
                ? `${description.trim().length} characters; this template allows ${version.slot_max_length}`
                : undefined
            }
            required
          >
            {(p) => (
              <Textarea
                {...p}
                rows={5}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            )}
          </Field>
          <p className="text-right text-xs text-text-muted" aria-live="polite">
            {description.trim().length} / {version.slot_max_length}
          </p>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <fieldset className="space-y-2">
            <legend className="mb-1 text-sm font-medium">Who signs in through the link</legend>
            {(
              [
                ["sso", "Employees, with their organisation account"],
                ["otp", "Anyone, with a one-time code (candidates, vendors, visitors)"],
              ] as const
            ).map(([value, label]) => (
              <label key={value} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="audience"
                  checked={audience === value}
                  onChange={() => setAudience(value)}
                  className="accent-[var(--accent)]"
                />
                {label}
              </label>
            ))}
          </fieldset>
          <Field label="The link works until" required>
            {(p) => (
              <Input
                {...p}
                type="date"
                value={expires}
                min={new Date().toISOString().slice(0, 10)}
                onChange={(e) => setExpires(e.target.value)}
              />
            )}
          </Field>
          <p className="text-xs text-text-muted">
            Creating the activity publishes its notice and opens its link at once. There is no
            approval step: Legal approved the version.
          </p>
        </div>
      )}

      <DialogFooter>
        <Button variant="ghost" onClick={step === 0 ? onDone : () => setStep(step - 1)}>
          {step === 0 ? "Cancel" : "Back"}
        </Button>
        {step < STEPS.length - 1 ? (
          <Button variant="primary" disabled={!ready[step]} onClick={() => setStep(step + 1)}>
            Next
          </Button>
        ) : (
          <Button
            variant="primary"
            disabled={!ready.every(Boolean)}
            loading={create.isPending}
            onClick={submit}
          >
            Create the activity
          </Button>
        )}
      </DialogFooter>
    </div>
  );
}
