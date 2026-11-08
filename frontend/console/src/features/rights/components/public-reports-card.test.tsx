/**
 * Reports from the public link (0065): what an access or erasure request finds
 * of the reports the requester sent that an office dismissed. The card draws
 * the server's answer: what it found, why it did not look, and whether the
 * name and email may be erased now and why not. Erasure is one act on the
 * request, after asking, and names no report.
 */
import { QueryClient } from "@tanstack/react-query";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PublicReportsCard } from "@/features/rights/components/public-reports-card";
import { keys } from "@/lib/query";
import { makeRequestDetail } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { RightsPublicReport, RightsPublicReports, RightsRequestDetail } from "@/types";

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const UUID = "99999999-9999-4999-8999-999999999999";

const report = (over: Partial<RightsPublicReport> = {}): RightsPublicReport => ({
  report_uuid: crypto.randomUUID(),
  reference: "INC-2026-0041",
  reporter_name: "Meera Iyer",
  reporter_email: "meera.iyer@example.com",
  title: "A test by the helpdesk",
  received_at: "2026-11-05T09:00:00Z",
  dismissed_at: "2026-11-05T12:00:00Z",
  reporter_erased_at: null,
  ...over,
});

const found = (over: Partial<RightsPublicReports> = {}): RightsPublicReports => ({
  looked: true,
  not_looked_because: null,
  items: [report()],
  total: 1,
  erased: 0,
  may_erase: true,
  erase_blocked_by: null,
  ...over,
});

const request = (
  public_reports: RightsPublicReports | null,
  over: Partial<RightsRequestDetail> = {},
) =>
  makeRequestDetail({
    request_type: "erasure",
    status: "in_progress",
    public_reports,
    ...over,
  });

const BUTTON = /^Erase their name and email from/;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PublicReportsCard", () => {
  it("shows nothing to a role the server hides them from", () => {
    const { container } = render(<PublicReportsCard request={request(null)} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("says why nothing was looked for, in the server's words", () => {
    render(
      <PublicReportsCard
        request={request(
          found({
            looked: false,
            not_looked_because:
              "Identity is not verified yet; nothing is looked for until it is.",
            items: [],
            total: 0,
            may_erase: false,
            erase_blocked_by:
              "Identity is not verified yet; nothing is looked for until it is.",
          }),
        )}
      />,
    );

    expect(
      screen.getByText("Identity is not verified yet; nothing is looked for until it is."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: BUTTON })).not.toBeInTheDocument();
  });

  describe("with no proved email address to look by", () => {
    const NO_PROVED_EMAIL =
      "No email address proved to be the requester's is held, so nothing was looked for.";
    const STILL_CARRIES = /carries an address that was looked for/;
    const notLooked = (over: Partial<RightsPublicReports> = {}) =>
      found({
        looked: false,
        not_looked_because: NO_PROVED_EMAIL,
        items: [],
        total: 0,
        erased: 0,
        may_erase: false,
        erase_blocked_by: NO_PROVED_EMAIL,
        ...over,
      });

    it("says nothing was looked for, and never that no report carries the email", () => {
      render(
        <PublicReportsCard request={request(notLooked(), { request_type: "access" })} />,
      );

      expect(screen.getByText(NO_PROVED_EMAIL)).toBeInTheDocument();
      expect(screen.queryByText(STILL_CARRIES)).not.toBeInTheDocument();
      expect(
        screen.queryByText("These go to them with the response."),
      ).not.toBeInTheDocument();
      expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
    });

    it("still lists what was erased under the request, below the reason", () => {
      render(
        <PublicReportsCard
          request={request(
            notLooked({
              items: [
                report({
                  reporter_name: null,
                  reporter_email: null,
                  reporter_erased_at: "2026-11-07T10:00:00Z",
                }),
              ],
              erased: 1,
            }),
          )}
        />,
      );

      expect(screen.getByText(NO_PROVED_EMAIL)).toBeInTheDocument();
      const [line] = screen.getAllByRole("listitem");
      expect(within(line).getByText("INC-2026-0041")).toBeInTheDocument();
      expect(within(line).getByText(/^Name and email erased /)).toBeInTheDocument();
      expect(screen.queryByText(STILL_CARRIES)).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: BUTTON })).not.toBeInTheDocument();
    });

    it("reads the request again when erasure is refused for it, and shows the server's sentence", async () => {
      server.use(
        http.post(`${API}/requests/${UUID}/public-reports/erase`, () =>
          HttpResponse.json(
            {
              error: { code: "no_proved_email", message: NO_PROVED_EMAIL, request_id: "r" },
            },
            { status: 409 },
          ),
        ),
      );
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });
      queryClient.setQueryData(keys.rights.detail(UUID), request(found()));
      const { user } = render(<PublicReportsCard request={request(found())} />, {
        queryClient,
      });

      await user.click(screen.getByRole("button", { name: BUTTON }));
      await user.click(
        within(await screen.findByRole("dialog")).getByRole("button", {
          name: "Erase name and email",
        }),
      );

      await vi.waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Not erased", NO_PROVED_EMAIL),
      );
      expect(queryClient.getQueryState(keys.rights.detail(UUID))?.isInvalidated).toBe(true);
    });
  });

  it("lists the dismissed reports sent from the requester's email address, and says how many more there are", () => {
    render(
      <PublicReportsCard
        request={request(
          found({
            items: [
              report(),
              report({
                reference: "INC-2026-0040",
                reporter_name: null,
                reporter_email: null,
                reporter_erased_at: "2026-11-07T10:00:00Z",
              }),
            ],
            total: 3,
            erased: 1,
          }),
        )}
      />,
    );

    const [first, second] = screen.getAllByRole("listitem");
    expect(within(first).getByText("INC-2026-0041")).toBeInTheDocument();
    expect(within(first).getByText("A test by the helpdesk")).toBeInTheDocument();
    expect(
      within(first).getByText("From Meera Iyer, meera.iyer@example.com"),
    ).toBeInTheDocument();
    expect(within(second).getByText(/^Name and email erased /)).toBeInTheDocument();
    // Fifty at most are listed; the count is of every one still naming them.
    expect(screen.getByText("And 2 more, not listed here.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Erase their name and email from 3 reports" }),
    ).toBeEnabled();
  });

  describe("with nothing found by the addresses looked for", () => {
    const EMPTY =
      "No dismissed report from the public link carries an address that was looked for. An account's email is looked for only once a code sent to it has come back, so the email shown for the requester may not have been.";
    const none = () =>
      found({
        items: [],
        total: 0,
        may_erase: false,
        erase_blocked_by:
          "No report from the public link still carries the requester's name and email.",
      });

    it("says no report carries an address looked for, and no more than the server knows", () => {
      // The server's answer for a person an earlier request erased: the report
      // came from them, but nothing on it finds them now.
      render(<PublicReportsCard request={request(none())} />);

      expect(screen.getByText(EMPTY)).toBeInTheDocument();
      expect(
        screen.queryByText(/came from this person's email address/),
      ).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: BUTTON })).not.toBeInTheDocument();
    });

    it("never says the email shown for an account was looked for", () => {
      // An account whose own email no code has come back from, beside a second
      // email that one has: the server looked by the second alone, found
      // nothing, and serves looked with no items. The request shows the first.
      render(
        <PublicReportsCard
          request={request(none(), {
            request_type: "access",
            subject_email: "meera.iyer@example.com",
          })}
        />,
      );

      expect(screen.getByText(EMPTY)).toBeInTheDocument();
      expect(screen.queryByText(/this person's email/)).not.toBeInTheDocument();
      expect(screen.queryByText(/meera\.iyer@example\.com/)).not.toBeInTheDocument();
    });
  });

  describe("the header", () => {
    it("calls no address proved, for a request with no account verified by hand", () => {
      render(
        <PublicReportsCard
          request={request(found(), {
            subject_uuid: null,
            subject_name: null,
            verification_method: "manual",
          })}
        />,
      );

      expect(screen.queryByText(/proved/)).not.toBeInTheDocument();
      expect(
        screen.getByText(
          /found by email once identity was verified: the address a request with no account gave, or an account's address once a code sent to it has come back, as at sign-up or sign-in\. A code from the rights form, one read back to an officer, or one that accepted a nomination on an account already there, does not count\./,
        ),
      ).toBeInTheDocument();
    });

    it("says only what was looked for, not whose reports they are", () => {
      render(<PublicReportsCard request={request(found())} />);

      expect(
        screen.getByText(
          /^Reports sent through the public link that an office did not take up,/,
        ),
      ).toBeInTheDocument();
      expect(screen.queryByText(/this person sent/)).not.toBeInTheDocument();
    });
  });

  it.each([
    [
      "a hold on an account the contact is on",
      "A legal hold on the requester stops this until it is released.",
    ],
    [
      "a hold check that could not be made",
      "The key service did not answer, so whether a legal hold covers the requester could not be checked. Reload to try again.",
    ],
  ])(
    "will not erase for a request with no account under %s, and says why as served",
    (_, why) => {
      render(
        <PublicReportsCard
          request={request(found({ may_erase: false, erase_blocked_by: why }), {
            subject_uuid: null,
            subject_name: null,
          })}
        />,
      );

      const button = screen.getByRole("button", { name: BUTTON });
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute("title", why);
      expect(screen.getByText(why)).toBeInTheDocument();
    },
  );

  it("erases the name and email after asking, and says what is kept", async () => {
    let asked = 0;
    let body: unknown = "nothing read";
    server.use(
      http.post(
        `${API}/requests/${UUID}/public-reports/erase`,
        async ({ request: sent }) => {
          asked += 1;
          body = await sent.json();
          return HttpResponse.json(
            found({
              items: [report({ reporter_erased_at: "2026-11-08T10:00:00Z" })],
              total: 0,
            }),
          );
        },
      ),
    );
    const { user } = render(<PublicReportsCard request={request(found())} />);

    await user.click(
      screen.getByRole("button", { name: "Erase their name and email from 1 report" }),
    );
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByText(/why it was dismissed and who dismissed it are kept/),
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/This cannot be undone/)).toBeInTheDocument();
    expect(asked).toBe(0);
    await user.click(within(dialog).getByRole("button", { name: "Erase name and email" }));

    await vi.waitFor(() => expect(asked).toBe(1));
    // The server finds the reports again itself: nothing names one.
    expect(body).toEqual({});
    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Erased",
        expect.stringContaining("are kept"),
      ),
    );
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("has the request and the Dismissed reports list read again once it has erased", async () => {
    server.use(
      http.post(`${API}/requests/${UUID}/public-reports/erase`, () =>
        HttpResponse.json(found({ total: 0 })),
      ),
    );
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const dismissed = [...keys.breach.intake(), "dismissed"];
    queryClient.setQueryData(dismissed, []);
    queryClient.setQueryData(keys.rights.detail(UUID), request(found()));
    const { user } = render(<PublicReportsCard request={request(found())} />, {
      queryClient,
    });

    await user.click(screen.getByRole("button", { name: BUTTON }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: "Erase name and email",
      }),
    );

    await vi.waitFor(() =>
      expect(queryClient.getQueryState(dismissed)?.isInvalidated).toBe(true),
    );
    expect(queryClient.getQueryState(keys.rights.detail(UUID))?.isInvalidated).toBe(true);
  });

  it("offers no erasure on an access request, and says the reports go with the response", () => {
    render(
      <PublicReportsCard
        request={request(
          found({ may_erase: false, erase_blocked_by: "Only an erasure request…" }),
          { request_type: "access" },
        )}
      />,
    );

    expect(screen.queryByRole("button", { name: BUTTON })).not.toBeInTheDocument();
    expect(screen.getByText("These go to them with the response.")).toBeInTheDocument();
  });

  it("will not erase while the server says not, and says why beside the button", () => {
    const why = "A legal hold on the requester stops this until it is released.";
    render(
      <PublicReportsCard
        request={request(found({ may_erase: false, erase_blocked_by: why }))}
      />,
    );

    const button = screen.getByRole("button", { name: BUTTON });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("title", why);
    expect(screen.getByText(why)).toBeInTheDocument();
  });

  it("shows the server's sentence when erasure is refused", async () => {
    const sentence = "A legal hold on the requester stops this until it is released.";
    server.use(
      http.post(`${API}/requests/${UUID}/public-reports/erase`, () =>
        HttpResponse.json(
          { error: { code: "legal_hold", message: sentence, request_id: "r" } },
          { status: 409 },
        ),
      ),
    );
    const { user } = render(<PublicReportsCard request={request(found())} />);

    await user.click(screen.getByRole("button", { name: BUTTON }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: "Erase name and email",
      }),
    );

    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Not erased", sentence),
    );
  });
});
