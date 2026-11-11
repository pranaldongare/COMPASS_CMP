/**
 * What an administrator can do to an account, from the register's row menu and
 * from the account's own page alike (2026-11-11).
 *
 * The page offered only Edit, and said the rest stayed on the register; the
 * product owner asked for every list action on the record too. One hook so the
 * two cannot drift: the same items, the same guards, the same dialogs.
 *
 * Acting on your own account is how an organisation ends up with no
 * administrator, so those items are absent there; resending an invitation is
 * only while it is pending - once somebody has a password the way back in is
 * theirs.
 */
"use client";

import { KeyRound, Send, ShieldEllipsis, UserCheck, UserX } from "lucide-react";
import * as React from "react";

import { ConfirmDialog, Dialog, DialogContent } from "@/components/ui/dialog";
import type { RowAction } from "@/components/ui/overlay";
import {
  useDeactivateUser,
  useForceLogout,
  useReactivateUser,
  useResendInvitation,
  useResetMfa,
} from "@/features/users";
import { RoleChangeForm } from "@/features/users/components/forms";
import { useAuth, useToast } from "@/providers";
import type { User } from "@/types";

function said(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function useAccountActions(): {
  /** Everything but View and Edit, which each page offers its own way. */
  actionsFor: (user: User) => RowAction[];
  /** Mount once on the page. */
  dialogs: React.ReactNode;
} {
  const { me } = useAuth();
  const toast = useToast();
  const deactivate = useDeactivateUser();
  const reactivate = useReactivateUser();
  const resetMfa = useResetMfa();
  const forceLogout = useForceLogout();
  const resendInvitation = useResendInvitation();
  const [changingRole, setChangingRole] = React.useState<User | null>(null);
  const [resettingMfa, setResettingMfa] = React.useState<User | null>(null);

  async function toggle(user: User) {
    const active = user.status === "active";
    try {
      if (active) {
        const result = await deactivate.mutateAsync(user.uuid);
        // Different acts behind one button, and the server's message says
        // which: a member of staff loses the role and keeps their account as a
        // data principal; a data principal's account is switched off; a
        // temporary ticket holder's breach-only login ends (S3-09).
        toast.success(
          user.role === "data_subject"
            ? "Account deactivated"
            : user.role === "breach_holder"
              ? "Temporary access ended"
              : "Staff access ended",
          result.message ?? "Every session was terminated immediately.",
        );
      } else {
        await reactivate.mutateAsync(user.uuid);
        toast.success("Account reactivated", `${user.full_name} can sign in again.`);
      }
    } catch (err) {
      toast.error("Could not update the account", said(err, "The change could not be applied."));
    }
  }

  async function invite(user: User) {
    try {
      const result = await resendInvitation.mutateAsync(user.uuid);
      toast.success("Invitation sent", result.message ?? undefined);
    } catch (err) {
      toast.error("Could not send the invitation", said(err, "The invitation could not be sent."));
    }
  }

  function actionsFor(u: User): RowAction[] {
    if (me?.role !== "admin") return [];
    return [
      ...(u.uuid !== me?.uuid && u.role !== "data_subject"
        ? [
            { label: "Change role", icon: ShieldEllipsis, onSelect: () => setChangingRole(u) },
            { label: "Reset MFA", icon: KeyRound, onSelect: () => setResettingMfa(u) },
          ]
        : []),
      ...(u.status === "pending" && u.role !== "data_subject"
        ? [
            {
              label: "Resend invitation",
              icon: Send,
              disabled: resendInvitation.isPending,
              onSelect: () => invite(u),
            },
          ]
        : []),
      ...(u.status === "deactivated"
        ? [
            {
              label: "Reactivate",
              icon: UserCheck,
              disabled: reactivate.isPending,
              onSelect: () => toggle(u),
            },
          ]
        : []),
      ...(u.uuid !== me?.uuid && u.status !== "deactivated"
        ? [
            {
              label:
                u.role === "data_subject"
                  ? "Deactivate"
                  : u.role === "breach_holder"
                    ? "End temporary access"
                    : "End staff access",
              icon: UserX,
              destructive: true,
              disabled: deactivate.isPending,
              onSelect: () => toggle(u),
            },
          ]
        : []),
    ];
  }

  const dialogs = (
    <>
      <Dialog open={Boolean(changingRole)} onOpenChange={(o) => !o && setChangingRole(null)}>
        <DialogContent title="Change role" description="Audited, and it ends every session.">
          {changingRole && <RoleChangeForm user={changingRole} onDone={() => setChangingRole(null)} />}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(resettingMfa)}
        onOpenChange={(o) => !o && setResettingMfa(null)}
        title={`Reset MFA for ${resettingMfa?.full_name ?? ""}?`}
        confirmLabel="Reset MFA"
        loading={resetMfa.isPending}
        tone="primary"
        consequence={
          <p>
            Their outstanding verification code is discarded and every session ends. They
            will be asked for a fresh code the next time they sign in. Use this when
            somebody has lost access to their email, not as routine maintenance.
          </p>
        }
        onConfirm={async () => {
          if (!resettingMfa) return;
          try {
            await resetMfa.mutateAsync(resettingMfa.uuid);
            await forceLogout.mutateAsync(resettingMfa.uuid);
            toast.success("MFA reset", "They must sign in again.");
            setResettingMfa(null);
          } catch (err) {
            toast.error("Could not reset MFA", said(err, "Please try again."));
          }
        }}
      />
    </>
  );

  return { actionsFor, dialogs };
}
