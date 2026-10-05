/**
 * Send waits for the breach to be recorded (S3-06), and says so in the
 * server's words: an incident still being validated may have its notice
 * drafted and approved, never sent.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { NoticesCard } from "@/features/breach/components/notices-card";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach, BreachNotices } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const UUID = "44444444-4444-4444-8444-444444444444";
const REASON =
  "Record the breach before anyone is notified: validate it as a personal data breach first";

const breach = { breach_uuid: UUID, status: "open" } as Breach;

function notices(over: Partial<BreachNotices>): BreachNotices {
  const words = {
    what_happened: "w",
    consequences: "c",
    measures: "m",
    protective_steps: "p",
    contact: "o",
  };
  return {
    versions: [
      {
        notice_uuid: "55555555-5555-4555-8555-555555555555",
        version: 1,
        state: "approved",
        ...words,
        created_at: "2026-10-05T10:00:00Z",
        approved_at: "2026-10-05T10:05:00Z",
        approved_by_name: "Priya Menon",
      },
    ] as unknown as BreachNotices["versions"],
    account: [],
    failures: [],
    listed: 3,
    unnotified: 3,
    contents: [],
    duty: "Principals notified",
    send_blocked_by: null,
    ...over,
  };
}

function serve(body: BreachNotices) {
  server.use(http.get(`${API}/breaches/${UUID}/notices`, () => HttpResponse.json(body)));
}

describe("NoticesCard", () => {
  it("holds Send while the incident is not recorded, and says why", async () => {
    serve(notices({ send_blocked_by: REASON }));
    render(<NoticesCard breach={breach} />);

    const send = await screen.findByRole("button", { name: "Send version 1" });
    expect(send).toBeDisabled();
    expect(screen.getByText(REASON)).toBeInTheDocument();
  });

  it("offers Send once the breach is recorded", async () => {
    serve(notices({ send_blocked_by: null }));
    render(<NoticesCard breach={breach} />);

    expect(await screen.findByRole("button", { name: "Send version 1" })).toBeEnabled();
    expect(screen.queryByText(REASON)).not.toBeInTheDocument();
  });
});
