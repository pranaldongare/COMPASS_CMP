/**
 * Whether an answer may call itself complete is the server's to say (S2-02).
 * The card reads `complete_blocked_by` and holds no copy of the rule: when the
 * server names a reason, Complete cannot be chosen and the reason is shown.
 */
import { describe, expect, it } from "vitest";

import { RespondCard } from "@/features/rights/components/respond-card";
import { ToastProvider } from "@/providers/toast-provider";
import { makeRequestDetail } from "@/test/fixtures";
import { fireEvent, render, screen } from "@/test/render";
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

  it("offers attaching files as a button, lists what was chosen and refuses what the server would", async () => {
    // 2026-11-12: the browser's own "Choose files" under the response was
    // not seen as something to press.
    const { user } = card();
    expect(screen.getByRole("button", { name: "Attach files" })).toBeInTheDocument();
    const picker = screen.getByLabelText(/Files released with the response/);

    await user.upload(picker, new File(["a,b\n1,2\n"], "extract.csv", { type: "text/csv" }));
    expect(screen.getByText("extract.csv")).toBeInTheDocument();

    // Not a kind the server takes: said here, and not added.
    // Past the picker's own filter, as a drag or an "All files" choice gets.
    fireEvent.change(picker, {
      target: { files: [new File(["MZ"], "tool.exe", { type: "application/octet-stream" })] },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("tool.exe is not a PDF, image, CSV or text file");
    expect(screen.queryByText(/^tool\.exe$/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove extract.csv" }));
    expect(screen.queryByText("extract.csv")).not.toBeInTheDocument();
  });
});
