/**
 * The two derivations the dashboard makes from its own payload.
 *
 * Pulled out because both are decisions rather than rendering: which counts a
 * chart has already explained (so they are not repeated as tiles), and what to
 * tell somebody about their own role. Both are testable here and were not
 * inside a 490-line component.
 */

import { Segment } from "@/components/ui/charts";

/**
 * Build the part-to-whole view of consent, from whichever counts this role got.
 *
 * Returns the keys it consumed so the caller can avoid printing the same number
 * twice. Returns null when the response does not carry enough to make an honest
 * whole — a composition chart missing a slice is worse than no chart.
 */
export function consentComposition(
  counts: Record<string, number>,
): { segments: Segment[]; consumed: string[] } | null {
  // Four states, counted apart by the server: every current record is in
  // exactly one. A total minus withdrawals used to be drawn as "still
  // standing", which counted declined and partial records as standing consent.
  const states = [
    "consents_full",
    "consents_partial",
    "consents_declined",
    "consents_withdrawn",
  ];
  if (states.every((key) => key in counts)) {
    return {
      segments: [
        {
          key: "full",
          label: "Agreed to all purposes",
          value: counts.consents_full ?? 0,
          color: "var(--viz-1)",
        },
        {
          key: "partial",
          label: "Agreed to some",
          value: counts.consents_partial ?? 0,
          color: "var(--viz-2)",
        },
        {
          key: "declined",
          label: "Declined",
          value: counts.consents_declined ?? 0,
          color: "var(--viz-neutral)",
        },
        {
          key: "withdrawn",
          label: "Withdrawn",
          value: counts.consents_withdrawn ?? 0,
          color: "var(--viz-3)",
        },
      ],
      consumed: [...states, "total_consents", "withdrawals"],
    };
  }

  return null;
}

export function roleBlurb(role: string | null | undefined): string {
  switch (role) {
    case "dpo":
      return "Notices awaiting publication, projects awaiting your review, and the consent position across the platform.";
    case "dco":
      return "Your approved projects, the links collecting against them, and anything that failed to reconcile on import.";
    case "dco_admin":
      return "Projects collected by a third party: which sites are still waiting for a data source, and who picks them up when you attach one.";
    case "rco":
      return "The collection your team runs itself — your approved projects, the links collecting against them, and anything that failed to reconcile on import.";
    case "rnd_user":
      return "Your projects and what each one needs from you before it can move forward.";
    case "admin":
      return "Invitations waiting, access problems, grievances about the DPO, and the processor and source registry.";
    default:
      return "What is waiting for you, and the state of the platform.";
  }
}
