/**
 * Whose an incident is (0073): an officer reassigns it to the other office
 * with a reason and goes back to the register; and the reporter is sent an
 * acknowledgement, asked first, and nothing else.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AcknowledgeReporter, BreachOfficeCard } from "@/features/breach/components/office-card";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach } from "@/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));
const who = vi.hoisted(() => ({ office: "rnd" as string | null }));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }));
vi.mock("@/providers", () => ({
  useToast: () => toast,
  useAuth: () => ({ me: { role: "dpo", office: who.office } }),
}));

const UUID = "11111111-1111-4111-8111-111111111111";
const breach = (over: Partial<Breach> = {}): Breach =>
  ({
    breach_uuid: UUID,
    reference: "INC-2026-0042",
    incident_reference: "INC-2026-0042",
    breach_reference: null,
    status: "open",
    office: "rnd",
    transferred: null,
    reported: null,
    ...over,
  }) as Breach;

const reported = (over: Partial<NonNullable<Breach["reported"]>> = {}) => ({
  reporter_name: "Asha Rao",
  reporter_email: "asha@example.org",
  received_at: "2026-11-17T08:00:00Z",
  noticed_at: null,
  cyber_attack: null,
  acknowledgements: 0,
  acknowledged_at: null,
  acknowledged_by_name: null,
  ...over,
});

beforeEach(() => {
  who.office = "rnd";
  push.mockClear();
});

describe("BreachOfficeCard", () => {
  it("reassigns to the other office with a reason and goes back to the register", async () => {
    let sent: unknown = null;
    server.use(
      http.post(`${API}/breaches/${UUID}/transfer`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ reference: "INC-2026-0042", office: "hr" });
      }),
    );
    const { user } = render(<BreachOfficeCard breach={breach()} />);
    expect(screen.getByText("With the DPO office")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reassign to the Legal office" }));
    expect(screen.getByText(/nothing\s+starts again/)).toBeInTheDocument();
    const go = screen.getByRole("button", { name: "Reassign" });
    expect(go).toBeDisabled();
    await user.type(screen.getByLabelText(/why it belongs/i), "The data is of employees.");
    await user.click(go);
    expect(sent).toEqual({ office: "hr", reason: "The data is of employees." });
    expect(push).toHaveBeenCalledWith("/breaches");
  });

  it("says where a reassigned one came from, and why", () => {
    render(
      <BreachOfficeCard
        breach={breach({
          office: "hr",
          transferred: {
            from_office: "rnd",
            at: "2026-11-17T09:00:00Z",
            transferred_by_name: "Dev Officer",
            transfer_reason: "The data is of employees.",
          },
        })}
      />,
    );
    expect(screen.getByText("With the Legal office")).toBeInTheDocument();
    expect(screen.getByText(/Reassigned from the DPO office .* by Dev Officer/)).toBeInTheDocument();
    expect(screen.getByText("The data is of employees.")).toBeInTheDocument();
  });

  it("offers nothing on a closed one, or to somebody with no office", () => {
    const { unmount } = render(<BreachOfficeCard breach={breach({ status: "closed" })} />);
    expect(screen.queryByRole("button", { name: /reassign/i })).not.toBeInTheDocument();
    unmount();
    who.office = null;
    render(<BreachOfficeCard breach={breach()} />);
    expect(screen.queryByRole("button", { name: /reassign/i })).not.toBeInTheDocument();
  });
});

describe("AcknowledgeReporter", () => {
  it("is nothing on an incident the office logged", () => {
    const { container } = render(<AcknowledgeReporter breach={breach()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("asks first, then sends only the acknowledgement", async () => {
    let posts = 0;
    server.use(
      http.post(`${API}/breaches/${UUID}/reporter/acknowledge`, () => {
        posts += 1;
        return HttpResponse.json(
          breach({ reported: reported({ acknowledgements: 1, acknowledged_at: "2026-11-17T09:30:00Z" }) }),
        );
      }),
    );
    const { user } = render(<AcknowledgeReporter breach={breach({ reported: reported() })} />);
    expect(screen.getByText("Not sent yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Send acknowledgement" }));
    const question = await screen.findByRole("dialog", { name: "Send an acknowledgement to the reporter?" });
    expect(within(question).getByText(/Nothing about what was found, decided or done is sent/)).toBeInTheDocument();
    expect(posts).toBe(0);
    await user.click(within(question).getByRole("button", { name: "Send acknowledgement" }));
    await vi.waitFor(() => expect(posts).toBe(1));
    expect(toast.success).toHaveBeenCalledWith("Acknowledgement sent", expect.any(String));
  });

  it("says when it was sent, and offers it again", () => {
    render(
      <AcknowledgeReporter
        breach={breach({
          reported: reported({
            acknowledgements: 2,
            acknowledged_at: "2026-11-17T09:30:00Z",
            acknowledged_by_name: "Dev Officer",
          }),
        })}
      />,
    );
    expect(screen.getByText(/^Sent .* by Dev Officer \(2 times in all\)$/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send acknowledgement again" })).toBeInTheDocument();
  });
});
