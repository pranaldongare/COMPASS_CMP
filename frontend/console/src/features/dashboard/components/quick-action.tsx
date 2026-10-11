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

import { Database, Link2, Plus, ShieldAlert, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/primitives";
import { RecordBreachForm } from "@/features/breach/components/record-breach";
import { NewTemplateButton } from "@/features/notice-templates/components/templates-panel";
import { ProjectForm } from "@/features/projects/components";
import { UserForm } from "@/features/users/components/forms";
import type { Me } from "@/types";

type Action = "incident" | "project" | "account" | "link" | "source";

function actionFor(me: Me | null | undefined): Action | null {
  if (!me) return null;
  // The breach register is the DPO's write alone; read off the grants the
  // server sent, as the Breaches page is.
  if (me.writes.includes("breach")) return "incident";
  if (me.role === "rnd_user") return "project";
  if (me.role === "admin") return "account";
  // The collection roles' starts (2026-10-10, the role-dashboard design): a
  // DCO Admin registers a source; a DCO or RCO issues a consent link from the
  // links register, where a link is minted for a chosen site.
  if (me.role === "dco_admin" && me.nav.includes("sources")) return "source";
  if ((me.role === "dco" || me.role === "rco") && me.nav.includes("links")) return "link";
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
    link: { label: "New consent link", icon: Link2 },
    source: { label: "Register a data source", icon: Database },
  }[action];
  const Icon = copy.icon;

  // These two start on their own register, which holds the form.
  if (action === "link" || action === "source") {
    return (
      <Button variant="primary" asChild>
        <Link href={action === "link" ? "/links" : "/sources?new=1"}>
          <Icon className="size-4" />
          {copy.label}
        </Link>
      </Button>
    );
  }

  return (
    <>
      <Button variant="primary" onClick={() => setOpen(true)}>
        <Icon className="size-4" />
        {copy.label}
      </Button>
      {/* The DPO's second start (2026-10-07): a notice written before the
          project that will use it exists. Secondary - the incident leads. */}
      {me?.role === "dpo" && <NewTemplateButton variant="secondary" size="md" />}
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
