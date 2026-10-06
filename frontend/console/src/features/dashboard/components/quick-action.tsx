/**
 * The one thing a role starts from scratch, at the top of its dashboard
 * (2026-10-06).
 *
 * The DPO logs an incident: the organisation's board is owed word within
 * thirty minutes of its being first noticed, so the button must not be a
 * menu and a page away. An R&D user registers a project, an administrator
 * provisions an account - each the start of that role's work, needing no
 * record to hang off. Collection owners and the DCO Admin get none: what they
 * begin - a link, a site, a source - belongs to a project or a site, which
 * their queues below already lead to.
 *
 * The same forms, and the same rule for who sees them, as the pages they
 * come from; the server refuses anyone else regardless.
 */
"use client";

import { Plus, ShieldAlert, UserPlus } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/primitives";
import { RecordBreachForm } from "@/features/breach/components/record-breach";
import { ProjectForm } from "@/features/projects/components";
import { UserForm } from "@/features/users/components/forms";
import type { Me } from "@/types";

type Action = "incident" | "project" | "account";

function actionFor(me: Me | null | undefined): Action | null {
  if (!me) return null;
  // The breach register is the DPO's write alone; read off the grants the
  // server sent, as the Breaches page is.
  if (me.writes.includes("breach")) return "incident";
  if (me.role === "rnd_user") return "project";
  if (me.role === "admin") return "account";
  return null;
}

export function QuickAction({ me }: { me: Me | null | undefined }) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const action = actionFor(me);
  if (!action) return null;

  const copy = {
    incident: { label: "Log an incident", icon: ShieldAlert },
    project: { label: "Register a project", icon: Plus },
    account: { label: "Provision an account", icon: UserPlus },
  }[action];
  const Icon = copy.icon;

  return (
    <>
      <Button variant="primary" onClick={() => setOpen(true)}>
        <Icon className="size-4" />
        {copy.label}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        {action === "incident" && (
          <DialogContent
            title="Log an incident"
            description="As it was noticed. Every time is entered, not filled in: the clocks run from what you type."
            size="lg"
          >
            {/* Lands on the incident itself once logged. */}
            <RecordBreachForm onDone={() => setOpen(false)} />
          </DialogContent>
        )}
        {action === "project" && (
          <DialogContent
            title="Register a project"
            description="Add the project details and select the teams involved. You can set up collection sites next."
          >
            <ProjectForm
              onDone={(created) => {
                setOpen(false);
                if (created) router.push(`/projects/${created.project_uuid}`);
              }}
            />
          </DialogContent>
        )}
        {action === "account" && (
          <DialogContent
            title="Provision an account"
            description="No password is set here - an email invites them to set their own."
            size="lg"
          >
            <UserForm onDone={() => setOpen(false)} />
          </DialogContent>
        )}
      </Dialog>
    </>
  );
}
