/**
 * The consent link keeps a person's progress through what goes wrong
 * (review 2026-10-01, UX-3).
 *
 * - An outage is not an invalid link. Telling somebody at a collection site
 *   to ask for a new link because the API blinked sends them away for good.
 * - A code, once accepted, is spent. If the notice then fails to load she
 *   must not be left on the code screen with a code that will not work twice.
 * - Asking for another code, or using another contact, must not mean
 *   starting over from a fresh link.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import ConsentPage from "@/app/c/[token]/page";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const TOKEN = "tok-ux3";

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: TOKEN }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => `/c/${TOKEN}`,
}));

const LINK = {
  valid: true,
  project_name: "Footfall study",
  site_label: "Campus A",
  notice_uuid: "00000000-0000-4000-8000-000000000001",
  available_languages: ["english"],
};

const NOTICE = {
  notice: {
    uuid: LINK.notice_uuid,
    code: "N-1",
    version: 1,
    withdraw_url: "/my-consents",
    exercise_rights_url: "/rights",
    board_complaint_url: "https://example.org",
    dpo_contact: "dpo@example.org",
    recipients_text: null,
  },
  project_name: LINK.project_name,
  site_label: LINK.site_label,
  language_code: "english",
  rendered_text: "We would like to photograph the entrance.",
  content_hash: "abc",
  purposes: [],
  served_at: "2026-10-05T10:00:00Z",
};

function failing(status: number, code = "service_unavailable") {
  return HttpResponse.json(
    { error: { code, message: "Unavailable", request_id: "t" } },
    { status },
  );
}

async function confirm(user: ReturnType<typeof render>["user"]) {
  await user.type(await screen.findByLabelText(/mobile number/i), "+919876500001");
  await user.click(screen.getByRole("button", { name: /send the code/i }));
  await user.type(await screen.findByLabelText(/six-digit code/i), "123456");
  await user.click(screen.getByRole("button", { name: /confirm and read the notice/i }));
}

describe("opening the link", () => {
  it("says an unknown link is not valid", async () => {
    server.use(http.get(`${API}/c/${TOKEN}`, () => failing(404, "link_invalid")));
    render(<ConsentPage />);
    expect(await screen.findByText(/this link is not valid/i)).toBeInTheDocument();
  });

  it("says an outage is an outage, and tries again when asked", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/c/${TOKEN}`, () => {
        calls += 1;
        return calls === 1 ? failing(503) : HttpResponse.json(LINK);
      }),
    );
    const { user } = render(<ConsentPage />);

    expect(await screen.findByText(/could not open this link just now/i)).toBeInTheDocument();
    expect(screen.queryByText(/this link is not valid/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByLabelText(/mobile number/i)).toBeInTheDocument();
  });
});

describe("after the code is accepted", () => {
  it("does not go back to the code screen when the notice fails to load", async () => {
    let served = 0;
    server.use(
      http.get(`${API}/c/${TOKEN}`, () => HttpResponse.json(LINK)),
      http.post(`${API}/c/${TOKEN}/otp`, () => HttpResponse.json({ ok: true, message: "" })),
      http.post(`${API}/c/${TOKEN}/otp/verify`, () =>
        HttpResponse.json({ ok: true, complete: true, remaining: [], message: "" }),
      ),
      http.get(`${API}/auth/me`, () => HttpResponse.json(makeMe({ is_minor: false }))),
      http.get(`${API}/c/${TOKEN}/notice`, () => {
        served += 1;
        return served === 1 ? failing(503) : HttpResponse.json(NOTICE);
      }),
    );
    const { user } = render(<ConsentPage />);
    await confirm(user);

    expect(await screen.findByText(/your contact is confirmed/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/six-digit code/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText(NOTICE.rendered_text)).toBeInTheDocument();
  });
});

describe("the code step", () => {
  it("sends another code without starting over", async () => {
    let sent = 0;
    server.use(
      http.get(`${API}/c/${TOKEN}`, () => HttpResponse.json(LINK)),
      http.post(`${API}/c/${TOKEN}/otp`, () => {
        sent += 1;
        return HttpResponse.json({ ok: true, message: "" });
      }),
    );
    const { user } = render(<ConsentPage />);
    await user.type(await screen.findByLabelText(/mobile number/i), "+919876500001");
    await user.click(screen.getByRole("button", { name: /send the code/i }));
    await screen.findByLabelText(/six-digit code/i);

    await user.click(screen.getByRole("button", { name: /send a new code/i }));
    expect(await screen.findByText(/a new code is on its way/i)).toBeInTheDocument();
    expect(sent).toBe(2);
  });

  it("goes back to choose a different contact", async () => {
    server.use(
      http.get(`${API}/c/${TOKEN}`, () => HttpResponse.json(LINK)),
      http.post(`${API}/c/${TOKEN}/otp`, () => HttpResponse.json({ ok: true, message: "" })),
    );
    const { user } = render(<ConsentPage />);
    await user.type(await screen.findByLabelText(/mobile number/i), "+919876500001");
    await user.click(screen.getByRole("button", { name: /send the code/i }));
    await screen.findByLabelText(/six-digit code/i);

    await user.click(screen.getByRole("button", { name: /use a different contact/i }));
    expect(await screen.findByLabelText(/mobile number/i)).toBeInTheDocument();
  });
});
