/**
 * Identity, by a code to a stored channel (0065). The server says whether a
 * code has somewhere to go (`code_channel`): the account's contact, or, with no
 * account, the address a dismissed report from the public link came from. With
 * nowhere to go the page says so and offers no code; when the server could not
 * tell, an officer is told to reload. For anyone the server does not answer, a
 * request with an account offers its contact, and one with none says only that
 * a code is the DPO's or the Legal office's: the server refuses anybody else
 * alike there (403 `officers_only`), whatever the register holds, and the page
 * claims no channel either way.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VerificationCard } from "@/features/rights/components/staff-actions";
import { makeMe, makeRequestDetail } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Me, RightsRequestDetail } from "@/types";

const auth = vi.hoisted(() => ({ me: null as Me | null }));
const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}));
vi.mock("@/providers", () => ({ useAuth: () => ({ me: auth.me }), useToast: () => toast }));

const NO_CHANNEL = /there is no stored channel/;
const FROM_A_REPORT =
  /Sent to the address a report the requester sent through the public link came from/;
const UNKNOWN =
  /could not be checked just now: the key service did not answer\. Reload to try again\./;
const OFFICERS_ONLY =
  "Only the DPO or the Legal office can send or confirm a code for a request with no account.";

/** A request waiting for its identity, from the public form. */
const waiting = (over: Partial<RightsRequestDetail> = {}) =>
  makeRequestDetail({
    status: "received",
    verification_status: "pending",
    verification_method: null,
    verified_at: null,
    ...over,
  });

const noAccount = { subject_uuid: null, subject_name: null } as const;

const offered = () => ({
  send: screen.queryByRole("button", { name: "Send a code" }),
  box: screen.queryByLabelText(/Code the requester read back/),
  confirm: screen.queryByRole("button", { name: "Confirm" }),
});

beforeEach(() => {
  vi.clearAllMocks();
  auth.me = makeMe({ role: "dpo" });
});

describe("VerificationCard", () => {
  it("offers a code to the account's contact", () => {
    render(<VerificationCard request={waiting({ code_channel: true })} />);

    expect(
      screen.getByText(
        /Sent to the contact we hold for Meera Iyer - never to what was typed/,
      ),
    ).toBeInTheDocument();
    const { send, box, confirm } = offered();
    expect(send).toBeInTheDocument();
    expect(box).toBeInTheDocument();
    expect(confirm).toBeInTheDocument();
  });

  it("offers a code to a dismissed reporter with no account, and never says there is no channel", async () => {
    let asked = 0;
    server.use(
      http.post(`${API}/requests/:uuid/verification/code`, () => {
        asked += 1;
        return HttpResponse.json(waiting({ ...noAccount, code_channel: true }));
      }),
    );
    const { user } = render(
      <VerificationCard request={waiting({ ...noAccount, code_channel: true })} />,
    );

    expect(screen.getByText(FROM_A_REPORT)).toBeInTheDocument();
    expect(
      screen.getByText(
        /never to what was typed on the form\. The public form may have sent one already\./,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(NO_CHANNEL)).not.toBeInTheDocument();
    const { send, box, confirm } = offered();
    expect(box).toBeInTheDocument();
    expect(confirm).toBeInTheDocument();
    await user.click(send as HTMLElement);
    // Asked first (2026-11-12): the pop-up says where the code goes, and
    // nothing is sent until the yes.
    const question = await screen.findByRole("dialog", { name: "Send a verification code?" });
    expect(within(question).getByText(/A one-time code goes to the requester now\./)).toBeInTheDocument();
    expect(within(question).getByText(/never to what was typed on the form/)).toBeInTheDocument();
    expect(asked).toBe(0);
    await user.click(within(question).getByRole("button", { name: "Send the code" }));

    await vi.waitFor(() => expect(asked).toBe(1));
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Code sent"));
  });

  it("says there is no stored channel when the server holds none, and offers no code", () => {
    render(<VerificationCard request={waiting({ ...noAccount, code_channel: false })} />);

    expect(
      screen.getByText(
        "No account matches this contact, so there is no stored channel. Verify manually, or close as not verified.",
      ),
    ).toBeInTheDocument();
    const { send, box, confirm } = offered();
    expect(send).not.toBeInTheDocument();
    expect(box).not.toBeInTheDocument();
    expect(confirm).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record as verified" })).toBeInTheDocument();
  });

  it.each([["dpo"], ["legal"]] as const)(
    "tells the %s to reload when the server could not check, and claims no channel either way",
    (role) => {
      auth.me = makeMe({ role });
      render(<VerificationCard request={waiting({ ...noAccount, code_channel: null })} />);

      expect(screen.getByText(UNKNOWN)).toBeInTheDocument();
      expect(screen.queryByText(NO_CHANNEL)).not.toBeInTheDocument();
      expect(offered().send).not.toBeInTheDocument();
    },
  );

  it("tells the administrator a code with no account is the officers', and claims no channel either way", async () => {
    // An about-the-DPO request with no account: the administrator acts on it,
    // and the server answers them nothing of the register.
    auth.me = makeMe({ role: "admin" });
    const { user } = render(
      <VerificationCard request={waiting({ ...noAccount, code_channel: null })} />,
    );

    expect(
      screen.getByText(`${OFFICERS_ONLY} Verify manually, or close as not verified.`),
    ).toBeInTheDocument();
    expect(screen.queryByText(NO_CHANNEL)).not.toBeInTheDocument();
    expect(screen.queryByText(FROM_A_REPORT)).not.toBeInTheDocument();
    expect(screen.queryByText(UNKNOWN)).not.toBeInTheDocument();
    const { send, box, confirm } = offered();
    expect(send).not.toBeInTheDocument();
    expect(box).not.toBeInTheDocument();
    expect(confirm).not.toBeInTheDocument();
    // The other ways stay.
    expect(screen.getByRole("button", { name: "Record as verified" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "No match, or not satisfied" }));
    expect(
      screen.getByRole("button", { name: "Close as not verified" }),
    ).toBeInTheDocument();
  });

  it("keeps to the account for the administrator on a request with one", () => {
    auth.me = makeMe({ role: "admin" });
    render(<VerificationCard request={waiting({ code_channel: null })} />);

    expect(
      screen.getByText(/Sent to the contact we hold for Meera Iyer/),
    ).toBeInTheDocument();
    expect(screen.queryByText(OFFICERS_ONLY, { exact: false })).not.toBeInTheDocument();
    expect(offered().send).toBeInTheDocument();
  });

  it.each([
    ["Send a code", "code"],
    ["Confirm", "confirm"],
  ] as const)(
    "shows the server's sentence when %s is refused as the officers', and offers the code no more",
    async (pressed, route) => {
      server.use(
        http.post(`${API}/requests/:uuid/verification/${route}`, () =>
          HttpResponse.json(
            { error: { code: "officers_only", message: OFFICERS_ONLY, request_id: "r" } },
            { status: 403 },
          ),
        ),
      );
      const { user } = render(
        <VerificationCard request={waiting({ ...noAccount, code_channel: true })} />,
      );
      if (pressed === "Confirm") {
        await user.type(offered().box as HTMLElement, "123456");
      }
      await user.click(screen.getByRole("button", { name: pressed }));
      // Asked first (2026-11-12): what goes to the requester is said in a pop-up.
      const question = await screen.findByRole("dialog");
      await user.click(
        within(question).getByRole("button", {
          name: pressed === "Confirm" ? "Confirm identity" : "Send the code",
        }),
      );

      await vi.waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Not done", OFFICERS_ONLY),
      );
      expect(await screen.findByText(OFFICERS_ONLY)).toBeInTheDocument();
      expect(screen.queryByText(FROM_A_REPORT)).not.toBeInTheDocument();
      const { send, box, confirm } = offered();
      expect(send).not.toBeInTheDocument();
      expect(box).not.toBeInTheDocument();
      expect(confirm).not.toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Record as verified" }),
      ).toBeInTheDocument();
    },
  );

  it("keeps to the account for an officer once the request is past where the server asks", () => {
    // Not waiting for collation's side of the line: the server does not ask.
    render(
      <VerificationCard
        request={waiting({ ...noAccount, status: "collating", code_channel: null })}
      />,
    );

    expect(screen.getByText(NO_CHANNEL)).toBeInTheDocument();
    expect(screen.queryByText(UNKNOWN)).not.toBeInTheDocument();
  });
});
