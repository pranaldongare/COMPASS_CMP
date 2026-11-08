/**
 * Identity, by a code to a stored channel (0065). The server says whether a
 * code has somewhere to go (`code_channel`): the account's contact, or, with no
 * account, the address a dismissed report from the public link came from. With
 * nowhere to go the page says so and offers no code; when the server could not
 * tell, an officer is told to reload. For anyone the server does not answer,
 * the account alone decides, as before.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VerificationCard } from "@/features/rights/components/staff-actions";
import { makeMe, makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";
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

  it("keeps to the account for a role the server does not answer", () => {
    auth.me = makeMe({ role: "admin" });
    const { unmount } = render(
      <VerificationCard request={waiting({ ...noAccount, code_channel: null })} />,
    );

    expect(screen.getByText(NO_CHANNEL)).toBeInTheDocument();
    expect(screen.queryByText(UNKNOWN)).not.toBeInTheDocument();
    expect(offered().send).not.toBeInTheDocument();
    unmount();

    render(<VerificationCard request={waiting({ code_channel: null })} />);
    expect(
      screen.getByText(/Sent to the contact we hold for Meera Iyer/),
    ).toBeInTheDocument();
    expect(offered().send).toBeInTheDocument();
  });

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
