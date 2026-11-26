/**
 * A processor's retention review on the portal (ADR 0047): the link shows
 * which review it is and where a code will go; the code opens it; the answer
 * needs a reason to anonymise or keep, and nobody is named.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import RetentionLinkPage from "@/app/retention/[token]/page";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG";

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: TOKEN }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => `/retention/${TOKEN}`,
}));

const link = (signedIn: boolean) => ({
  reference: "RET-2026-11-0007-0003",
  holder_label: "Vision Labs Ltd",
  kind: "retention",
  code_goes_to: "p•••@vision.example",
  status: "open",
  due_at: "2026-12-26T18:29:00Z",
  signed_in: signedIn,
});

const detail = (status = "open", outcome: string | null = null) => ({
  action: {
    action_uuid: "a1",
    label: "Vision Labs Ltd",
    status,
    outcome,
    reason: null,
    keep_until: null,
    due_at: "2026-12-26T18:29:00Z",
    answered_at: null,
    sent_back_reason: null,
  },
  review: {
    reference: "RET-2026-11-0007-0003",
    kind: "retention",
    project_name: "Gait study",
    is_activity: false,
    purpose_code: "PUR-0003",
    purpose_name: "Model training",
    people: 42,
    first_due_at: "2026-11-02T00:00:00Z",
    last_due_at: "2026-11-02T00:00:00Z",
  },
});

describe("a processor's retention review", () => {
  it("opens with a code sent to the address the link went to", async () => {
    let verified = false;
    server.use(
      http.get(`${API}/retention-links/${TOKEN}`, () => HttpResponse.json(link(false))),
      http.post(`${API}/retention-links/${TOKEN}/code`, () =>
        HttpResponse.json({ ok: true, message: "A code is on its way." }),
      ),
      http.post(`${API}/retention-links/${TOKEN}/verify`, () => {
        verified = true;
        return HttpResponse.json({ ok: true });
      }),
      http.get(`${API}/retention-links/${TOKEN}/action`, () =>
        verified
          ? HttpResponse.json(detail())
          : HttpResponse.json(
              { error: { code: "code_needed", message: "x", request_id: "t" } },
              { status: 401 },
            ),
      ),
    );
    const { user } = render(<RetentionLinkPage />);

    expect(await screen.findByText("p•••@vision.example")).toBeInTheDocument();
    expect(screen.queryByText("Gait study")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText(/six-digit code/i), "123456");
    await user.click(screen.getByRole("button", { name: "Open the review" }));

    expect(await screen.findByText("Gait study")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("asks why before data is anonymised, then sends the answer", async () => {
    let sent: unknown = null;
    server.use(
      http.get(`${API}/retention-links/${TOKEN}`, () => HttpResponse.json(link(true))),
      http.get(`${API}/retention-links/${TOKEN}/action`, () => HttpResponse.json(detail())),
      http.post(`${API}/retention-links/${TOKEN}/answer`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(detail("answered", "anonymised"));
      }),
    );
    const { user } = render(<RetentionLinkPage />);

    await user.click(await screen.findByLabelText(/^Anonymised/));
    await user.click(screen.getByRole("button", { name: "Send the answer" }));
    expect(await screen.findByText(/each need a reason/i)).toBeInTheDocument();
    expect(sent).toBeNull();

    await user.type(screen.getByLabelText(/^Reason/), "Faces blurred.");
    await user.click(screen.getByRole("button", { name: "Send the answer" }));
    expect(await screen.findByText(/you answered: anonymised/i)).toBeInTheDocument();
    expect(sent).toMatchObject({ outcome: "anonymised", reason: "Faces blurred." });
  });
});
