/**
 * Suspending a processor or a data source, from its own page (2026-11-11).
 *
 * The register offered it in each row's menu and the record's page did not, so
 * somebody reading a record had to go back to the list to act on it. Asked
 * first here: the page is where somebody reads what they are about to stop.
 */
"use client";

import { Ban } from "lucide-react";
import * as React from "react";

import { ConfirmDialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/primitives";
import { useSuspendProcessor, useSuspendSource } from "@/features/registry";
import { useToast } from "@/providers";

const WORDS = {
  processor: {
    noun: "Processor",
    consequence: "It can no longer be assigned to a site. Sites already run by it keep it.",
    done: (name: string) => `${name} can no longer be assigned to a site.`,
  },
  source: {
    noun: "Source",
    consequence: "Imports from it are refused from now on. What was imported stays.",
    done: (name: string) => `Imports from ${name} are now refused.`,
  },
} as const;

export function SuspendRecord({
  kind,
  uuid,
  name,
}: {
  kind: keyof typeof WORDS;
  uuid: string;
  name: string;
}) {
  const toast = useToast();
  const processor = useSuspendProcessor();
  const source = useSuspendSource();
  const suspend = kind === "processor" ? processor : source;
  const words = WORDS[kind];
  const [asking, setAsking] = React.useState(false);

  return (
    <>
      <Button variant="danger" size="sm" onClick={() => setAsking(true)}>
        <Ban className="size-4" />
        Suspend
      </Button>
      <ConfirmDialog
        open={asking}
        onOpenChange={setAsking}
        title={`Suspend ${name}?`}
        confirmLabel={`Suspend ${words.noun.toLowerCase()}`}
        loading={suspend.isPending}
        consequence={<p>{words.consequence}</p>}
        onConfirm={async () => {
          try {
            await suspend.mutateAsync(uuid);
            toast.success(`${words.noun} suspended`, words.done(name));
            setAsking(false);
          } catch (err) {
            toast.error(
              "Suspension failed",
              err && typeof err === "object" && "userMessage" in err
                ? (err as { userMessage: () => string }).userMessage()
                : `Could not suspend the ${words.noun.toLowerCase()}.`,
            );
          }
        }}
      />
    </>
  );
}
