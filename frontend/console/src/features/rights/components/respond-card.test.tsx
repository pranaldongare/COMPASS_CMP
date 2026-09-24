/**
 * Whether an answer may call itself complete is the server's to say (S2-02).
 * The card reads `complete_blocked_by` and holds no copy of the rule: when the
 * server names a reason, Complete cannot be chosen and the reason is shown.
 */
import { describe, expect, it } from "vitest";

import { RespondCard } from "@/features/rights/components/respond-card";
import { ToastProvider } from "@/providers/toast-provider";
import { makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import type { RightsRequestDetail } from "@/types";

const collating = {
  status: "collating" as const,
  request_type: "erasure" as const,
  transitions: [{ to: "closed" as const, allowed: true, via: "respond" as const }],
};

function card(overrides: Partial<RightsRequestDetail> = {}) {
  return render(
    <ToastProvider>
      <RespondCard request={makeRequestDetail({ ...collating, ...overrides })} />
    </ToastProvider>,
  );
}

describe("RespondCard", () => {
  it("offers Complete when the server raises nothing against it", () => {
    card();
    expect(screen.getByRole("option", { name: "Complete" })).not.toBeDisabled();
    expect(screen.getByRole("combobox", { name: /outcome/i })).toHaveValue("complete");
  });

  it("holds Complete back and says why, in the server's words", () => {
    const why = "Not carried out yet: ASSET-7. The response can go out on time, but it is partial and says what remains.";
    card({ complete_blocked_by: why });
    expect(screen.getByRole("option", { name: "Complete" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: /outcome/i })).toHaveValue("partial");
    expect(screen.getByText(why)).toBeInTheDocument();
  });
});
