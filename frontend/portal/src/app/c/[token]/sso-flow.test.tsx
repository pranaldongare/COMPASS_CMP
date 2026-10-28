/**
 * An employee link signs in through her organisation (ADR 0034).
 *
 * - An `sso` link offers "Continue with your organisation account" and no
 *   contact box, and sends the browser where the start says.
 * - A provider that does not answer is said to be that, never a bad link.
 * - Back with `?sso=mobile`, she confirms a mobile and goes on to the notice.
 * - Back with `?sso=conflict`, she is told to ask the administrator.
 */
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import ConsentPage from "@/app/c/[token]/page";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const TOKEN = "tok-sso";

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: TOKEN }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => `/c/${TOKEN}`,
}));

const LINK = {
  valid: true,
  project_name: "Wellness week",
  site_label: "Wellness week",
  notice_uuid: "00000000-0000-4000-8000-000000000002",
  available_languages: ["english"],
  audience_mode: "sso",
};

const NOTICE = {
  notice: {
    uuid: LINK.notice_uuid,
    code: "HR-WELLNESS-2026",
    version: 1,
    withdraw_url: "/my-consents",
    exercise_rights_url: "/rights",
    board_complaint_url: "https://example.org",
    dpo_contact: "legal@example.org",
    recipients_text: null,
  },
  project_name: LINK.project_name,
  site_label: LINK.site_label,
  language_code: "english",
  rendered_text: "Four lunchtime sessions on sleep and stress.",
  content_hash: "abc",
  purposes: [],
  served_at: "2026-10-28T10:00:00Z",
};

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("An sso link", () => {
  it("offers the organisation's sign-in and nothing else", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign, search: "", pathname: `/c/${TOKEN}` });
    server.use(
      http.get(`${API}/c/${TOKEN}`, () => HttpResponse.json(LINK)),
      http.get(`${API}/c/${TOKEN}/sso/start`, () =>
        HttpResponse.json({ redirect_url: "https://idp.example/authorize?x=1" }),
      ),
    );
    const { user } = render(<ConsentPage />);
    const go = await screen.findByRole("button", {
      name: /continue with your organisation account/i,
    });
    expect(screen.queryByLabelText(/mobile number/i)).not.toBeInTheDocument();
    await user.click(go);
    expect(assign).toHaveBeenCalledWith("https://idp.example/authorize?x=1");
    vi.unstubAllGlobals();
  });

  it("says the service did not answer, not that the link is bad", async () => {
    server.use(
      http.get(`${API}/c/${TOKEN}`, () => HttpResponse.json(LINK)),
      http.get(`${API}/c/${TOKEN}/sso/start`, () =>
        HttpResponse.json(
          { error: { code: "sso_unavailable", message: "Not available", request_id: "t" } },
          { status: 503 },
        ),
      ),
    );
    const { user } = render(<ConsentPage />);
    await user.click(
      await screen.findByRole("button", { name: /continue with your organisation account/i }),
    );
    expect(await screen.findByText(/did not answer/i)).toBeInTheDocument();
    expect(screen.queryByText(/this link is not valid/i)).not.toBeInTheDocument();
  });

  it("asks a new employee for a mobile, then opens the notice", async () => {
    window.history.replaceState(null, "", `/c/${TOKEN}?sso=mobile`);
    server.use(
      http.get(`${API}/c/${TOKEN}`, () => HttpResponse.json(LINK)),
      http.post(`${API}/c/${TOKEN}/sso/mobile`, () =>
        HttpResponse.json({ ok: true, message: "Sent" }),
      ),
      http.post(`${API}/c/${TOKEN}/sso/mobile/verify`, () =>
        HttpResponse.json({ ok: true, message: "Confirmed" }),
      ),
      http.get(`${API}/auth/me`, () =>
        HttpResponse.json(makeMe({ role: "data_subject", is_minor: false })),
      ),
      http.get(`${API}/c/${TOKEN}/notice`, () => HttpResponse.json(NOTICE)),
    );
    const { user } = render(<ConsentPage />);
    await user.type(await screen.findByLabelText(/mobile number/i), "+919876500009");
    await user.click(screen.getByRole("button", { name: /send a code/i }));
    await user.type(await screen.findByLabelText(/the code we sent/i), "123456");
    await user.click(screen.getByRole("button", { name: /^confirm$/i }));
    expect(await screen.findByText(/four lunchtime sessions/i)).toBeInTheDocument();
  });

  it("tells somebody whose identity could not be matched to ask the administrator", async () => {
    window.history.replaceState(null, "", `/c/${TOKEN}?sso=conflict`);
    server.use(http.get(`${API}/c/${TOKEN}`, () => HttpResponse.json(LINK)));
    render(<ConsentPage />);
    expect(await screen.findByText(/contact the administrator/i)).toBeInTheDocument();
  });
});
