/**
 * Which office answers a request (0055): an intake request offers a claim
 * to an officer; a held one offers a transfer, which asks for the reason,
 * sends it, and goes back to the register.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { OfficeCard, officeTitle } from "@/features/rights/components/office-card";
import { makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
  useAuth: () => ({ me: { role: "legal", office: "hr" } }),
}));

describe("officeTitle", () => {
  it("names both offices and the intake", () => {
    expect(officeTitle("rnd")).toBe("DPO office");
    expect(officeTitle("hr")).toBe("Legal office");
    expect(officeTitle(null)).toBe("Shared intake");
  });
});

describe("OfficeCard", () => {
  it("offers a claim on a request in the shared intake", async () => {
    let claimed = false;
    server.use(
      http.post(`${API}/requests/:uuid/claim`, () => {
        claimed = true;
        return HttpResponse.json(makeRequestDetail({ office: "hr" }));
      }),
    );
    const { user } = render(<OfficeCard request={makeRequestDetail({ office: null })} />);
    expect(screen.getByText(/in the shared intake/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /transfer/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /claim for my office/i }));
    expect(claimed).toBe(true);
  });

  it("transfers with a reason and goes back to the register", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API}/requests/:uuid/transfer`, async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          request_uuid: "99999999-9999-4999-8999-999999999999",
          reference: "RR-2026-000001",
          office: "rnd",
        });
      }),
    );
    const { user } = render(<OfficeCard request={makeRequestDetail({ office: "hr" })} />);
    expect(screen.getByText(/with the legal office/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /transfer to the dpo office/i }));
    const go = screen.getByRole("button", { name: /^transfer$/i });
    expect(go).toBeDisabled();
    await user.type(screen.getByLabelText(/why it belongs/i), "A research project's data.");
    await user.click(go);
    expect(sent).toEqual({ office: "rnd", reason: "A research project's data." });
    expect(push).toHaveBeenCalledWith("/requests");
  });

  it("shows where a transferred request came from, and why", () => {
    render(
      <OfficeCard
        request={makeRequestDetail({
          office: "hr",
          transferred_from: "rnd",
          transferred_at: "2026-10-28T09:00:00Z",
          transfer_reason: "Her consent is to a wellness activity.",
        })}
      />,
    );
    expect(screen.getByText(/transferred from the dpo office/i)).toBeInTheDocument();
    expect(screen.getByText("Her consent is to a wellness activity.")).toBeInTheDocument();
  });
});
