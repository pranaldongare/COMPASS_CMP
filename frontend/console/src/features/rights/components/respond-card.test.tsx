/**
 * Whether an answer may call itself complete is the server's to say (S2-02).
 * The card reads `complete_blocked_by` and holds no copy of the rule: when the
 * server names a reason, Complete cannot be chosen and the reason is shown.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { RespondCard } from "@/features/rights/components/respond-card";
import { ToastProvider } from "@/providers/toast-provider";
import { makeRequestDetail } from "@/test/fixtures";
import { fireEvent, render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
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

  it("asks before a response is released, says what the requester is sent, and sends nothing on Cancel", async () => {
    // 2026-11-12: whatever goes to a data principal is asked about first.
    let released = 0;
    server.use(
      http.post(`${API}/requests/:uuid/respond`, () => {
        released += 1;
        return HttpResponse.json(makeRequestDetail({ status: "closed" }));
      }),
    );
    const { user } = card({ reference: "RR-2026-0042" });
    await user.type(screen.getByLabelText(/The response/), "Everything was erased on 3 November.");
    await user.upload(
      screen.getByLabelText(/Files released with the response/),
      new File(["a,b\n"], "extract.csv", { type: "text/csv" }),
    );

    await user.click(screen.getByRole("button", { name: "Release and close" }));
    const question = await screen.findByRole("dialog", {
      name: "Release the response to RR-2026-0042 and close it?",
    });
    expect(
      within(question).getByText(
        /The requester is emailed that the response is ready, and 1 file is released to their account\./,
      ),
    ).toBeInTheDocument();
    expect(within(question).getByText(/A response sent cannot be recalled\./)).toBeInTheDocument();
    await user.click(within(question).getByRole("button", { name: "Cancel" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(released).toBe(0);
    // What was typed and attached is still there.
    expect(screen.getByLabelText(/The response/)).toHaveValue("Everything was erased on 3 November.");
    expect(screen.getByText("extract.csv")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Release and close" }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", { name: "Release and close" }),
    );
    await vi.waitFor(() => expect(released).toBe(1));
  });

  it("asks before a grievance is decided, and says when the earlier request is run again", async () => {
    let decided: unknown = null;
    server.use(
      http.post(`${API}/requests/:uuid/decide`, async ({ request }) => {
        decided = await request.json();
        return HttpResponse.json({ ...makeRequestDetail({ status: "closed" }), rerun_reference: "RR-2026-0099" });
      }),
    );
    const { user } = card({
      reference: "RR-2026-0050",
      request_type: "grievance",
      linked_reference: "RR-2026-0042",
      transitions: [],
    });
    await user.type(screen.getByLabelText(/What was found, and why/), "The first answer left out the March files.");
    await user.type(screen.getByLabelText(/Remedy/), "The request is run again, at no cost.");

    await user.click(screen.getByRole("button", { name: "Decide and close" }));
    const question = await screen.findByRole("dialog", {
      name: "Decide RR-2026-0050 as upheld and close it?",
    });
    expect(
      within(question).getByText(/The requester is emailed your decision and the remedy, and the grievance closes\./),
    ).toBeInTheDocument();
    expect(within(question).getByText(/RR-2026-0042 is run again as a new request/)).toBeInTheDocument();
    expect(decided).toBeNull();

    await user.click(within(question).getByRole("button", { name: "Decide and close" }));
    await vi.waitFor(() => expect(decided).toMatchObject({ upheld: true, rerun: true }));
  });
});
