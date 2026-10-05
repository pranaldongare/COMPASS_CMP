/**
 * Nominations: who may act for you, and whom you may act for.
 *
 * They sat at the foot of My requests, below every request - one account had
 * 48 cards above them (UX review 2026-10-05). They have their own page and
 * their own place in the menu now; the reference a nominee is asked for is
 * found here.
 */
"use client";

import { PageHeader } from "@/components/layout/app-shell";
import { NominationCard } from "@/features/rights/components/nomination-card";
import { NomineeOfCard } from "@/features/rights/components/nominee-of-card";

export default function MyNominationsPage() {
  return (
    <>
      <PageHeader
        title="My nominations"
        description="Name someone to act for you if you die or cannot act, and see who has named you."
      />
      <div className="space-y-6">
        {/* First: something somebody else needs from you is more pressing
            than something you may one day arrange. Absent when there is none. */}
        <NomineeOfCard />
        <NominationCard />
      </div>
    </>
  );
}
